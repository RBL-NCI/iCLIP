import pandas as pd
import re
import sys
from datetime import datetime


def check_header(input_df,expected_list,check_file,error_log):
    check =  all(item in list(input_df.columns.values) for item in expected_list)

    if check is False:
        error_log.append("The file {} does not include all required elements:{}\n".format(check_file,set(expected_list).difference(set(list(input_df.columns.values)))))

    return(error_log)

def check_multiplex(input_df,select_file,error_log):
    for select_cols in input_df.columns.values:
        tmp_list = input_df[select_cols].tolist()

        #file_name
        if select_cols == "file_name":
            #check if all filenames are unique
            if len(tmp_list) != len(set(tmp_list)):
                error_log.append("File names must be unique: {}\n".format(set([x for x in tmp_list if tmp_list.count(x) > 1])))

        #check all filenames end in .fastq.gz
            for item in tmp_list:
                if not (item.endswith('.fastq.gz')):
                    error_log.append("All items in file_name column must end in fastq.gz - please update filename: {}\n".format(item))

        #multiplex
        if select_cols == "multiplex":
            #check values are alpha/numeric or _
            regex = re.compile(r'[A-Z]_[a-z][0-9]')
            for item in tmp_list:
                if(regex.search(item) != None):
                    error_log.append("{} values can only contain alpha/numeric values or _ - please review: {}\n".format(select_cols,item))
    return(error_log)

def check_samples(input_df,select_file,error_log):
    for select_cols in input_df.columns.values:
        tmp_list = input_df[select_cols].tolist()

        if select_cols == "sample":
            #check if col values are unique
            if len(tmp_list) != len(set(tmp_list)):
                error_log.append("{} names must be unique in {}: {}".format(select_cols,select_file,set([x for x in tmp_list if tmp_list.count(x) > 1])))
            #check values are alpha/numeric or _
            regex = re.compile(r'[A-Z]_[a-z][0-9]')
            for item in tmp_list:
                if(regex.search(item) != None):
                    error_log.append("{} values can only contain alpha/numeric values or _ - please review: {}".format(select_cols,item))

        if select_cols == "multiplex":
            for item in tmp_list :
                #check samples for unique barcodes
                sub_df = input_df[input_df[select_cols] == item]
                bc_list = sub_df["barcode"].tolist()

                if len(bc_list) != len(set(bc_list)):
                    error_log.append("Barcodes must be unique by sample in {}: sample {} contains duplicate barcodes {}".format(select_file,item,set([x for x in bc_list if bc_list.count(x) > 1])))

                #check values are alpha
                for item in bc_list:
                    if(item.isalpha() != True):
                        error_log.append("Barcode values can only contain alpha characters- please review: {}".format(item))

        #adaptor in samples.tsv
        if select_cols=="adaptor":
          #check values are alpha
          for item in tmp_list:
              if(item.isalpha() != True):
                  error_log.append("{} values can only contain alpha characters- please review: {}".format(select_cols,item))

    return(error_log)

def check_both_files(input_df_m,input_df_s,error_log):
    l1 = list(input_df_m.multiplex.unique())
    l2 = list(input_df_s.multiplex.unique())

    l_1to2 = list(set(l1)-set(l2))
    l_2to1 = list(set(l2)-set(l1))

    if len(l_1to2) != 0 or len(l_2to1) != 0:
        error_log.append("Multiplex ID's must be consistent between both files.")

    if len(l_1to2) !=0:
        error_log.append("The following was only found in the multiplex tsv: {}".format(l_1to2))

    if len(l_2to1) !=0:
        error_log.append("The following was only found in the sample tsv: {}".format(l_2to1))

    return(error_log)

error_log=[]

#Check multiplex file
check_file = sys.argv[2]
m_df = pd.read_csv(check_file,sep="\t")
m_req = ['file_name','multiplex']
error_log = check_header(m_df,m_req,check_file,error_log)
error_log = check_multiplex(m_df,check_file,error_log)

#Check samples file
check_file = sys.argv[3]
s_df = pd.read_csv(check_file,sep="\t")
s_req = ['multiplex','barcode','sample','adaptor']
error_log = check_header(s_df,s_req,check_file,error_log)
error_log = check_samples(s_df,check_file,error_log)

#Check concordance between two files
error_log = check_both_files(m_df,s_df,error_log)


#print out error_log
if len(error_log)==0:
    new_path = str(sys.argv[1]) + "clean.txt"
    f = open(new_path,"w+")
    f.close()
else:
    date_str = '%s%s_%s' % (sys.argv[1],'errors',datetime.now().strftime('%Y%m%d%H'))
    new_path =  date_str + '.txt'
    open(new_path, 'w+').write('\n'.join(error_log))
