import numpy as np
import pickle


def read_fasta():
    uniprot_seq_dict = {}
    f = open('./fileprocessing/output/out6.1_target_uniprot_pdb.fasta')
    for line in f.readlines():
        if line[0] == '>':
            pdbid = line.split('_')[0][1:]
            name = line.strip().split('_')[-1]
        else:
            seq = line.strip()
            uniprot_seq_dict[pdbid] = (seq, name)
    f.close()
    return uniprot_seq_dict


def get_pdbid_to_ligand():
    pdbid_to_ligand = {}
    with open('./fileprocessing/pdbbind_index/INDEX_general_PL.2020') as f:
        for line in f.readlines():
            if line[0] != '#':
                ligand = line.strip().split('(')[1].split(')')[0]
                if '-mer' in ligand:
                    continue
                elif '/' in ligand:
                    ligand = ligand.split('/')[0]
                if len(ligand) != 3:
                    # print(line[:4], ligand)
                    continue
                pdbid_to_ligand[line[:4]] = ligand
    # print('pdbid_to_ligand',len(pdbid_to_ligand))
    return pdbid_to_ligand


pdbid_to_ligand = get_pdbid_to_ligand()


def get_result_dict():
    result_dict = {}
    f = open('./fileprocessing/output/out6.3_pdb_align.txt')
    i = -1
    seq_target, seq_query, align = '', '', ''
    pdb_ratio_dict = {}
    for line in f.readlines():
        i += 1
        if i % 4 == 0:
            if 'target_name' in line:
                if len(seq_target) != 0:
                    result_dict[target_name] = (seq_target, seq_query, align, target_start, query_start)
                target_name = line.strip().split(' ')[-1]
                # print('target_name',target_name)
                seq_target, seq_query, align = '', '', ''
            else:
                seq_target += line.split('\t')[1]
            # print('seq_target',seq_target)
        elif i % 4 == 1:
            if 'query_name' in line:
                query_name = line.strip().split(' ')[-1]
            # print('query_name',query_name)
            else:
                align += line.strip('\n').split('\t')[1]
            # print('align',align)
        elif i % 4 == 2:
            if 'optimal_alignment_score' in line:
                for item in line.strip().split('\t'):
                    if item.split(' ')[0] == 'target_begin:':
                        target_start = int(item.split(' ')[1])
                    elif item.split(' ')[0] == 'query_begin:':
                        query_start = int(item.split(' ')[1])
            else:
                seq_query += line.split('\t')[1]
    f.close()
    return result_dict


def seq_with_gap_to_idx(seq):
    idx_list = []
    i = 0
    for aa in seq:
        if aa == '-':
            idx_list.append(-1)
        else:
            idx_list.append(i)
            i += 1
    return idx_list


def get_target_idx(target_idx_list, query_idx_list, align, target_start, query_start):
    pdb_to_uniprot_idx = []
    for i in range(target_start - 1):
        pdb_to_uniprot_idx.append(-1)
    for i in range(len(target_idx_list)):
        if target_idx_list[i] != -1:
            if align[i] == '|' and query_idx_list[i] != -1:
                pdb_to_uniprot_idx.append(query_idx_list[i] + query_start - 1)
            else:
                pdb_to_uniprot_idx.append(-1)
    return pdb_to_uniprot_idx


def get_pdb_to_uniprot_map(result_dict):
    # pdb_ratio_dict = {}
    pdb_to_uniprot_map_dict = {}
    for name in result_dict:
        pdbid, chain = name.split('_')
        seq_target, seq_query, align, target_start, query_start = result_dict[name]
        ratio = float(align.count('|')) / float(len(seq_target.replace('-', '')))
        if ratio < 0.9:
            continue

        target_idx_list = seq_with_gap_to_idx(seq_target)
        query_idx_list = seq_with_gap_to_idx(seq_query)
        pdb_to_uniprot_idx = get_target_idx(target_idx_list, query_idx_list, align, target_start, query_start)
        if pdbid in pdb_to_uniprot_map_dict:
            pdb_to_uniprot_map_dict[pdbid][chain] = pdb_to_uniprot_idx
        else:
            pdb_to_uniprot_map_dict[pdbid] = {}
            pdb_to_uniprot_map_dict[pdbid][chain] = pdb_to_uniprot_idx
    return pdb_to_uniprot_map_dict


def get_interact_in_uniprot_seq(pdb_to_uniprot, uniprot_seq, seq_dict, residue_interact):
    interact_in_uniprot_seq_list = []
    residue_bond_type = []
    interact_in_uniprot_seq_set = set()
    residue_record = ''
    for item in residue_interact:
        chain, idx = item[0][0], int(item[0][1:])  # chain, idx (pdb) of interact residue
        if chain not in pdb_to_uniprot:
            continue
        sequence, idx_list = seq_dict[chain]  # pdb seuqnce, idx of chain
        if idx_list.count(idx) != 1:  # some positions in pdb sequence may have the same idx
            print('idx_list.count(idx) != 1')
        seq_pos = idx_list.index(idx)  # position along pdb sequence
        if seq_pos >= len(pdb_to_uniprot[chain]):
            continue
        if pdb_to_uniprot[chain][seq_pos] == -1:
            continue
        interact_idx = pdb_to_uniprot[chain][seq_pos]
        # if interact_idx not in interact_in_uniprot_seq_set:
        interact_in_uniprot_seq_set.add(interact_idx)
        interact_in_uniprot_seq_list.append(interact_idx)
        residue_bond_type.append((interact_idx, item[2]))
        residue_record += item[1]  # for check
    return interact_in_uniprot_seq_list, residue_record, residue_bond_type, chain


if __name__ == '__main__':
    # main
    with open('./fileprocessing/output/out1.2_pdbid_list.txt') as f:
        pdbid_list = [line.strip() for line in f.readlines()]

    with open('./fileprocessing/output/out4_interaction_dict', 'rb') as f:
        interaction_dict_from_pdb = pickle.load(f)

    pdbid_to_ligand = get_pdbid_to_ligand()
    result_dict = get_result_dict()
    pdb_to_uniprot_map_dict = get_pdb_to_uniprot_map(result_dict)

    i = 0
    count_no_uniprot_map = 0
    count_not_in_uniprot_seq_dict = 0
    uniprot_seq_dict = read_fasta()
    interaction_dict_from_pdb_final = {}
    valid_pdbid = []
    chain_valid = {}

    for item in interaction_dict_from_pdb:
        pdbid, ligand = item.split('_')
        i += 1
        if pdbid in ['4p4s', '5ayf']:  # sequences are not same
            continue
        if pdbid not in uniprot_seq_dict:
            count_not_in_uniprot_seq_dict += 1
            continue
        if pdbid not in pdb_to_uniprot_map_dict:
            count_no_uniprot_map += 1
            continue
        valid_pdbid.append(pdbid)
        ligand = pdbid_to_ligand[pdbid]  # get ligand id
        uniprot_seq, uniprot_id = uniprot_seq_dict[pdbid]  # get uniprot sequence

        seq_dict = interaction_dict_from_pdb[pdbid + '_' + ligand]['sequence']  # get pdb seq_dict
        residue_interact = interaction_dict_from_pdb[pdbid + '_' + ligand]['residue_interact']  # get pdb residue_interact

        assert residue_interact is not None

        pdb_to_uniprot = pdb_to_uniprot_map_dict[pdbid]
        interact_in_uniprot_seq_list, residue_record, residue_bond_type, chain\
            = get_interact_in_uniprot_seq(pdb_to_uniprot, uniprot_seq, seq_dict, residue_interact)
        # Add chain into list
        chain_valid[pdbid] = chain
        assert residue_record == ''.join(np.array([aa for aa in uniprot_seq])[
                                             interact_in_uniprot_seq_list].tolist()), pdbid  # check if uniprot aa is the same as contact aa

        sequence = interaction_dict_from_pdb[pdbid + '_' + ligand]['sequence'][chain]

        interaction_dict_from_pdb_final[pdbid] = {}
        interaction_dict_from_pdb_final[pdbid]['ligand'] = ligand
        interaction_dict_from_pdb_final[pdbid]['uniprot_id'] = uniprot_id
        interaction_dict_from_pdb_final[pdbid]['uniprot_seq'] = sequence
        interaction_dict_from_pdb_final[pdbid]['interact_in_uniprot_seq'] = interact_in_uniprot_seq_list
        interaction_dict_from_pdb_final[pdbid]['residue_bond_type'] = residue_bond_type
        interaction_dict_from_pdb_final[pdbid]['chain'] = chain
    print('interaction_dict_from_pdb_final', len(interaction_dict_from_pdb_final))
    print('count_no_uniprot_map', count_no_uniprot_map)
    print('count_not_in_uniprot_seq_dict', count_not_in_uniprot_seq_dict)

    with open('./fileprocessing/output/FEATNN_final_interaction_dict', 'wb') as f:
        pickle.dump(interaction_dict_from_pdb_final, f, protocol=0)
    f.close()

    with open('./fileprocessing/output/chain_dict', 'wb') as f:
        pickle.dump(chain_valid, f, protocol=0)
    f.close()

    print('Valid pdbid: ', len(valid_pdbid))
    with open('./fileprocessing/output/valid_pdbid', 'wb') as f:
        pickle.dump(valid_pdbid, f, protocol=0)
    f.close()