import argparse
import math
import time
import pickle
from tqdm import tqdm
import numpy as np
import random
import os

import torch
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader

import transformer.Constants as Constants
from transformer.Models import Transformer
from transformer.Optim import ScheduledOptim
from transformer.modern_data import TransformerDataset, collate_fn

def cal_performance(pred, gold, trg_pad_idx, smoothing=False):
    loss = cal_loss(pred, gold, trg_pad_idx, smoothing=smoothing)
    pred = pred.max(1)[1]
    gold = gold.contiguous().view(-1)
    non_pad_mask = gold.ne(trg_pad_idx)
    n_correct = pred.eq(gold).masked_select(non_pad_mask).sum().item()
    n_word = non_pad_mask.sum().item()
    return loss, n_correct, n_word

def cal_loss(pred, gold, trg_pad_idx, smoothing=False):
    gold = gold.contiguous().view(-1)
    if smoothing:
        eps = 0.1
        n_class = pred.size(1)
        one_hot = torch.zeros_like(pred).scatter(1, gold.view(-1, 1), 1)
        one_hot = one_hot * (1 - eps) + (1 - one_hot) * eps / (n_class - 1)
        log_prb = F.log_softmax(pred, dim=1)
        non_pad_mask = gold.ne(trg_pad_idx)
        loss = -(one_hot * log_prb).sum(dim=1)
        loss = loss.masked_select(non_pad_mask).sum()
    else:
        loss = F.cross_entropy(pred, gold, ignore_index=trg_pad_idx, reduction='sum')
    return loss

def train_epoch(model, training_data, optimizer, opt, device, smoothing):
    model.train()
    total_loss, n_word_total, n_word_correct = 0, 0, 0 
    for src_seq, trg_seq in tqdm(training_data, mininterval=2, desc='  - (Training)   ', leave=False):
        src_seq = src_seq.to(device)
        trg_seq = trg_seq.to(device)
        gold = trg_seq[:, 1:].contiguous().view(-1)
        trg_seq = trg_seq[:, :-1]

        optimizer.zero_grad()
        pred = model(src_seq, trg_seq)

        loss, n_correct, n_word = cal_performance(pred, gold, opt.trg_pad_idx, smoothing=smoothing) 
        loss.backward()
        optimizer.step_and_update_lr()

        n_word_total += n_word
        n_word_correct += n_correct
        total_loss += loss.item()

    return total_loss/n_word_total, n_word_correct/n_word_total

def eval_epoch(model, validation_data, device, opt):
    model.eval()
    total_loss, n_word_total, n_word_correct = 0, 0, 0
    with torch.no_grad():
        for src_seq, trg_seq in tqdm(validation_data, mininterval=2, desc='  - (Validation) ', leave=False):
            src_seq = src_seq.to(device)
            trg_seq = trg_seq.to(device)
            gold = trg_seq[:, 1:].contiguous().view(-1)
            trg_seq = trg_seq[:, :-1]

            pred = model(src_seq, trg_seq)
            loss, n_correct, n_word = cal_performance(pred, gold, opt.trg_pad_idx, smoothing=False)

            n_word_total += n_word
            n_word_correct += n_correct
            total_loss += loss.item()

    return total_loss/n_word_total, n_word_correct/n_word_total

def train(model, training_data, validation_data, optimizer, device, opt):
    if opt.use_tb:
        from torch.utils.tensorboard import SummaryWriter
        tb_writer = SummaryWriter(log_dir=os.path.join(opt.output_dir, 'tensorboard'))

    log_train_file = os.path.join(opt.output_dir, 'train.log')
    log_valid_file = os.path.join(opt.output_dir, 'valid.log')

    with open(log_train_file, 'w') as log_tf, open(log_valid_file, 'w') as log_vf:
        log_tf.write('epoch,loss,ppl,accuracy\n')
        log_vf.write('epoch,loss,ppl,accuracy\n')

    valid_losses = []
    for epoch_i in range(opt.epoch):
        print(f'[ Epoch {epoch_i} ]')

        start = time.time()
        train_loss, train_accu = train_epoch(model, training_data, optimizer, opt, device, opt.label_smoothing)
        train_ppl = math.exp(min(train_loss, 100))
        lr = optimizer._optimizer.param_groups[0]['lr']
        print(f'  - (Training)   ppl: {train_ppl: 8.5f}, accuracy: {100*train_accu:3.3f} %, lr: {lr:8.5f}, elapse: {(time.time()-start)/60:3.3f} min')

        start = time.time()
        valid_loss, valid_accu = eval_epoch(model, validation_data, device, opt)
        valid_ppl = math.exp(min(valid_loss, 100))
        print(f'  - (Validation) ppl: {valid_ppl: 8.5f}, accuracy: {100*valid_accu:3.3f} %, elapse: {(time.time()-start)/60:3.3f} min')

        valid_losses += [valid_loss]
        checkpoint = {'epoch': epoch_i, 'settings': opt, 'model': model.state_dict(), 'vocab': opt.vocab}

        if opt.save_mode == 'best' and valid_loss <= min(valid_losses):
            torch.save(checkpoint, os.path.join(opt.output_dir, 'model.chkpt'))
            print('    - [Info] The checkpoint file has been updated.')

        with open(log_train_file, 'a') as log_tf, open(log_valid_file, 'a') as log_vf:
            log_tf.write(f'{epoch_i},{train_loss: 8.5f},{train_ppl: 8.5f},{100*train_accu:3.3f}\n')
            log_vf.write(f'{epoch_i},{valid_loss: 8.5f},{valid_ppl: 8.5f},{100*valid_accu:3.3f}\n')

        if opt.use_tb:
            tb_writer.add_scalars('ppl', {'train': train_ppl, 'val': valid_ppl}, epoch_i)
            tb_writer.add_scalars('accuracy', {'train': train_accu*100, 'val': valid_accu*100}, epoch_i)
            tb_writer.add_scalar('learning_rate', lr, epoch_i)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-data_pkl', required=True)
    parser.add_argument('-epoch', type=int, default=10)
    parser.add_argument('-b', '--batch_size', type=int, default=256)
    parser.add_argument('-d_model', type=int, default=512)
    parser.add_argument('-d_inner_hid', type=int, default=2048)
    parser.add_argument('-d_k', type=int, default=64)
    parser.add_argument('-d_v', type=int, default=64)
    parser.add_argument('-n_head', type=int, default=8)
    parser.add_argument('-n_layers', type=int, default=6)
    parser.add_argument('-warmup','--n_warmup_steps', type=int, default=4000)
    parser.add_argument('-lr_mul', type=float, default=2.0)
    parser.add_argument('-seed', type=int, default=1)
    parser.add_argument('-dropout', type=float, default=0.1)
    parser.add_argument('-embs_share_weight', action='store_true')
    parser.add_argument('-proj_share_weight', action='store_true')
    parser.add_argument('-scale_emb_or_prj', type=str, default='prj')
    parser.add_argument('-output_dir', type=str, default='output')
    parser.add_argument('-use_tb', action='store_true')
    parser.add_argument('-save_mode', type=str, choices=['all', 'best'], default='best')
    parser.add_argument('-no_cuda', action='store_true')
    parser.add_argument('-label_smoothing', action='store_true')

    opt = parser.parse_args()
    opt.cuda = not opt.no_cuda
    opt.d_word_vec = opt.d_model

    torch.manual_seed(opt.seed)
    np.random.seed(opt.seed)
    random.seed(opt.seed)

    if not os.path.exists(opt.output_dir): os.makedirs(opt.output_dir)

    device = torch.device('cuda' if opt.cuda else 'cpu')

    print(f'[Info] Loading data from {opt.data_pkl}')
    with open(opt.data_pkl, 'rb') as f:
        data = pickle.load(f)
    
    opt.src_vocab_size = len(data['vocab']['src'])
    opt.trg_vocab_size = len(data['vocab']['trg'])
    opt.src_pad_idx = data['vocab']['src'].stoi[Constants.PAD_WORD]
    opt.trg_pad_idx = data['vocab']['trg'].stoi[Constants.PAD_WORD]
    opt.vocab = data['vocab']

    train_loader = DataLoader(
        TransformerDataset(data['train']['src'], data['train']['trg']),
        num_workers=2, batch_size=opt.batch_size, shuffle=True,
        collate_fn=lambda x: collate_fn(x, opt.src_pad_idx, opt.trg_pad_idx))

    valid_loader = DataLoader(
        TransformerDataset(data['valid']['src'], data['valid']['trg']),
        num_workers=2, batch_size=opt.batch_size,
        collate_fn=lambda x: collate_fn(x, opt.src_pad_idx, opt.trg_pad_idx))

    model = Transformer(
        opt.src_vocab_size, opt.trg_vocab_size,
        src_pad_idx=opt.src_pad_idx, trg_pad_idx=opt.trg_pad_idx,
        trg_emb_prj_weight_sharing=opt.proj_share_weight,
        emb_src_trg_weight_sharing=opt.embs_share_weight,
        d_k=opt.d_k, d_v=opt.d_v, d_model=opt.d_model, d_word_vec=opt.d_word_vec,
        d_inner=opt.d_inner_hid, n_layers=opt.n_layers, n_head=opt.n_head,
        dropout=opt.dropout, scale_emb_or_prj=opt.scale_emb_or_prj).to(device)

    optimizer = ScheduledOptim(
        optim.Adam(model.parameters(), betas=(0.9, 0.98), eps=1e-09),
        opt.lr_mul, opt.d_model, opt.n_warmup_steps)

    train(model, train_loader, valid_loader, optimizer, device, opt)

if __name__ == '__main__':
    main()
