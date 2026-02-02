import argparse
import pickle
import spacy
from tqdm import tqdm
from transformer.modern_data import Vocabulary
import transformer.Constants as Constants
from collections import Counter

def load_data(path_src, path_trg):
    with open(path_src, 'r', encoding='utf-8') as f:
        src_lines = [line.strip() for line in f]
    with open(path_trg, 'r', encoding='utf-8') as f:
        trg_lines = [line.strip() for line in f]
    return src_lines, trg_lines

def tokenize(lines, nlp):
    tokenized = []
    for doc in tqdm(nlp.pipe(lines, batch_size=1000, n_process=4), total=len(lines)):
        tokenized.append([tok.text.lower() for tok in doc])
    return tokenized

def build_vocab(tokenized_lines, min_freq):
    counter = Counter()
    for tokens in tokenized_lines:
        counter.update(tokens)
    return Vocabulary.build(counter, min_freq=min_freq)

def convert_to_indices(tokenized_lines, vocab):
    indices = []
    for tokens in tokenized_lines:
        inst = [vocab.stoi.get(Constants.BOS_WORD)] + \
               [vocab.stoi.get(tok, vocab.stoi[Constants.UNK_WORD]) for tok in tokens] + \
               [vocab.stoi.get(Constants.EOS_WORD)]
        indices.append(inst)
    return indices

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-train_src', required=True)
    parser.add_argument('-train_trg', required=True)
    parser.add_argument('-val_src', required=True)
    parser.add_argument('-val_trg', required=True)
    parser.add_argument('-save_data', required=True)
    parser.add_argument('-max_len', type=int, default=100)
    parser.add_argument('-min_word_count', type=int, default=3)
    parser.add_argument('-share_vocab', action='store_true')
    
    opt = parser.parse_args()
    
    print('[Info] Loading SpaCy models...')
    nlp_src = spacy.load('de_core_news_sm')
    nlp_trg = spacy.load('en_core_web_sm')
    
    print('[Info] Loading and tokenizing training data...')
    train_src_raw, train_trg_raw = load_data(opt.train_src, opt.train_trg)
    train_src_tok = tokenize(train_src_raw, nlp_src)
    train_trg_tok = tokenize(train_trg_raw, nlp_trg)
    
    print('[Info] Loading and tokenizing validation data...')
    val_src_raw, val_trg_raw = load_data(opt.val_src, opt.val_trg)
    val_src_tok = tokenize(val_src_raw, nlp_src)
    val_trg_tok = tokenize(val_trg_raw, nlp_trg)
    
    print('[Info] Building vocabulary...')
    if opt.share_vocab:
        combined_tok = train_src_tok + train_trg_tok
        vocab_src = vocab_trg = build_vocab(combined_tok, opt.min_word_count)
    else:
        vocab_src = build_vocab(train_src_tok, opt.min_word_count)
        vocab_trg = build_vocab(train_trg_tok, opt.min_word_count)
    
    print(f'[Info] Source vocab size: {len(vocab_src)}')
    print(f'[Info] Target vocab size: {len(vocab_trg)}')
    
    print('[Info] Converting to indices...')
    data = {
        'settings': opt,
        'vocab': {'src': vocab_src, 'trg': vocab_trg},
        'train': {
            'src': convert_to_indices(train_src_tok, vocab_src),
            'trg': convert_to_indices(train_trg_tok, vocab_trg)
        },
        'valid': {
            'src': convert_to_indices(val_src_tok, vocab_src),
            'trg': convert_to_indices(val_trg_tok, vocab_trg)
        }
    }
    
    print(f'[Info] Saving to {opt.save_data}')
    with open(opt.save_data, 'wb') as f:
        pickle.dump(data, f)

if __name__ == '__main__':
    main()
