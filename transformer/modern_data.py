import torch
from torch.utils.data import Dataset

class TransformerDataset(Dataset):
    def __init__(self, src_insts, trg_insts):
        assert len(src_insts) == len(trg_insts)
        self.src_insts = src_insts
        self.trg_insts = trg_insts

    def __len__(self):
        return len(self.src_insts)

    def __getitem__(self, idx):
        return self.src_insts[idx], self.trg_insts[idx]

def collate_fn(insts, src_pad_idx, trg_pad_idx):
    src_insts, trg_insts = list(zip(*insts))
    
    # Pad sequences
    max_src_len = max(len(s) for s in src_insts)
    max_trg_len = max(len(t) for t in trg_insts)
    
    src_batch = [s + [src_pad_idx] * (max_src_len - len(s)) for s in src_insts]
    trg_batch = [t + [trg_pad_idx] * (max_trg_len - len(t)) for t in trg_insts]
    
    return torch.LongTensor(src_batch), torch.LongTensor(trg_batch)

class Vocabulary:
    def __init__(self, stoi, itos):
        self.stoi = stoi
        self.itos = itos
    
    def __len__(self):
        return len(self.itos)

    @classmethod
    def build(cls, counter, min_freq=1, specials=['<blank>', '<unk>', '<s>', '</s>']):
        itos = specials[:]
        stoi = {tok: i for i, tok in enumerate(itos)}
        for tok, freq in counter.items():
            if freq >= min_freq and tok not in stoi:
                itos.append(tok)
                stoi[tok] = len(itos) - 1
        return cls(stoi, itos)
