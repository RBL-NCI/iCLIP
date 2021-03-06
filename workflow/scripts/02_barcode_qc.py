import matplotlib.pyplot as plt
import HTSeq
import itertools
from collections import Counter
import pandas as pd
import sys
import json

#NOTE
#Current script is set up for two barcoding strategies - if additional are required they 
# must be added below. Current accepted formats include:
#NNNNNCACTGTNNNN = total len 15, seq len 6, position [5:11]
#NNNTGGCNN = total len 9, seq len 4, position [3:7]

#args
sample_manifest = sys.argv[1] #"samples_example.tsv"
multiplex_manifest = sys.argv[2] #"multiplex_example.tsv"
fastq_dir = sys.argv[3]
output_dir = sys.argv[4]
mismatch = sys.argv[5]

def CreateSampleDicts(df_m,df_s):
    s_dict={}
    m_dict={}

    #create dict that maps multiplex: sampleid : barcode
    for multi_name in df_s['multiplex'].unique():
        sub_df = df_s[df_s['multiplex']==multi_name]
        s_dict[multi_name]={}

        #each row maps to a sample:barcode and sample:group
        for index,row in sub_df.iterrows():
            sample_name = row['sample']
            s_dict[multi_name][sample_name]=row['barcode']

    #creat dict that maps mulitplex: filename
    m_dict = dict(zip(df_m.multiplex, df_m.file_name))

    return(m_dict,s_dict)

#Read manifests, create dicts
df_multiplex = pd.read_csv(multiplex_manifest,sep="\t")
df_samples = pd.read_csv(sample_manifest,sep="\t")
(multiplex_dict,samp_dict) = CreateSampleDicts(df_multiplex,df_samples)

for k,v in multiplex_dict.items():
    bc_dict = {}
    fastq_file = HTSeq.FastqReader(fastq_dir + v)
  
    #create expected bc list
    bc_exp=[]
    for k2,v2 in samp_dict[k].items():
        bc_exp.append(v2.replace('N',''))

    #generate list of possible barcodes with 1 bp variation
    bc_mutants={}
    nuc_list = ['A','T','C','G','N']

    #check the number of mismatches requested is possible given the expected barcodes
    for a, b in itertools.combinations(bc_exp, 2):
        #zip two barcodes andn compare each letter
        compare=zip(a,b)
        diff_list=[]
        #print (a,b)
        for i,j in compare:
            #if the letters are a mismatch, add to list
            if i!=j:
                diff_list.append(j)
            #if the mismatch list is not > than the mismatch value requested, print error and fail
        if(len(diff_list)<1 + int(mismatch)):
            print('The number of differences ({}) between barcodes {} and {} is less than or equal to the number of mismatches requested ({})'. format(len(diff_list),a,b,mismatch))
            
            sys.exit('Barcode strategy requires differences between barcodes is greater than mismatch allowance')

    # for each expected barcode
    for bc in bc_exp:
        #vary the string by one bp, push str to dict with expected value as the dict key
        for i in range(0,len(list(bc))):
            for nuc in nuc_list:
                tmp = list(bc)
                tmp[i]=nuc
                bc_mutants["".join(tmp)]=bc

                #if more than 1 mismatch is allowed, repeat variation
                if(int(mismatch)==2):
                    for j in range(0,len(list(bc))):
                        for nuc in nuc_list:
                            tmp2 = list("".join(tmp))
                            tmp2[j]=nuc
                            bc_mutants["".join(tmp2)]=bc
    
    #determine bc length for one bc
    bc_length = len(samp_dict[k][k2])

    #create counts of barcodes for each sample
    for read in fastq_file:
        
        #change position of bc depending on length of barcode
        if bc_length == 15:
            #change seq from bit to str, remove extra ' added with bit
            barcode = read.seq[5:11].decode("utf-8").replace('\'','') 
        elif bc_length == 9:
            #change seq from bit to str, remove extra ' added with bit
            barcode = read.seq[3:7].decode("utf-8").replace('\'','')
        else:
            sys.exit('Barcode strategy only approved for length of 9 and 15 bp')
        
        #if barcode matches mutant, change barcode to expected value
        if barcode in bc_mutants:
            barcode_update = barcode
            barcode = bc_mutants[barcode_update]
        
        #create barcode:sample:count 
        if k not in bc_dict:
            bc_dict[k]={} 
        bc_dict[k][barcode] = bc_dict[k].get(barcode, 0) + 1

    #select top 5 barcodes for each sample
    top_dict = dict(Counter(bc_dict[k]).most_common(5))
    
    #compare observed bc list with expected bc list, write output to text
    bc_obs=[]
    for k2,v2 in top_dict.items():
        bc_obs.append(k2)
        
    check =  all(item in bc_obs for item in bc_exp)
    if check is True:
        file_save = output_dir + k + '/00_qc_post/' + k + '_barcode.txt'
        f = open(file_save,"w+")
        f.write("\n* SampleID {}\n".format(k))
        f.write("\t + Number of mismatches allowed {}\n".format(mismatch))
        f.write("\t + The top barcodes identified {} include the expected barcodes {}\n\n".format(bc_obs, bc_exp))
        f.write("\t + List of top barcodes:counts \n")
        f.write("\t\t + " + json.dumps(top_dict))

        f.close()    
    else :
        file_save = output_dir + k + '_barcode_errors.txt'
        f = open(file_save,"w+")
        f.write("The top barcodes identified {} were not congruent with expected barcode list {}. Review associated img for more information.".format(bc_obs, bc_exp)) 
        f.close()

    #print barplot for top barcodes
    file_save = output_dir + k + '/00_qc_post/' + k + '_barcode.png'
    plt.bar(*zip(*top_dict.items()))
    plt.suptitle('Top 5 Barcodes: ' + k + '\n Number of mismatches allowed: ' + mismatch)
    plt.xticks(rotation='45', fontsize=6)
    for k,v in top_dict.items():
        plt.text(x=k , y =v+1 , s=str(v), color = 'black', fontweight='bold')
    plt.tight_layout()
    plt.savefig(file_save)


"""
#Testing
print(dict(sorted(bc_dict.items(), key=lambda item: item[1])))
python workflow/scripts/02_barcode_qc.py /data/RBL_NCI/iCLIP/test/sample_mm10_one.tsv /data/RBL_NCI/iCLIP/test/multiplex_mm10_one.tsv /data/RBL_NCI/iCLIP/test/ /data/sevillas2/iCLIP/test/ 1

python workflow/scripts/02_barcode_qc.py /data/RBL_NCI/Wolin/CLIP_Pipeline/iCLIP/fCLIP/sam_test/samples.tsv /data/RBL_NCI/Wolin/CLIP_Pipeline/iCLIP/fCLIP/sam_test/multiplex.tsv /data/RBL_NCI/Wolin/CLIP_Pipeline/iCLIP/fCLIP/sam_test/ /data/sevillas2/iCLIP/marco/ 1


for read in itertools.islice(fastq_file, 2000):
"""
