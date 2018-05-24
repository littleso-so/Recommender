'''
Created on April 9, 2018

@author: ming
'''

import os
import sys
import cPickle as pickl
import numpy as np

from operator import itemgetter
from scipy.sparse.csr import csr_matrix

from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn import preprocessing
import random
import re
from tensorflow.contrib import learn



class Data_Factory():

    def load(self, path):
        R = pickl.load(open(path + "/ratings.all", "rb"))
        print "Load preprocessed rating data - %s" % (path + "/ratings.all")
        D_all = pickl.load(open(path + "/document.all", "rb"))
        print "Load preprocessed document data - %s" % (path + "/document.all")
        return R,D_all
        return
        '''
        #user information, and item information respectively.
        
        U_all = pickl.load(open(path+"/user_review.all","rb"))
        print "Load preprocessed user review data {}".format(path+"/user_review.all")
        V_all = pickl.load(open(path+"/movie_review.all",'rb'))
        print "Load preprocessed movie review data {}".format(path+"/moview_review.all")
        return R, D_all,U_all,V_all
        '''
    def save(self, path, R, D_all,U_all,V_all,user_info=''):
        if not os.path.exists(path):
            os.makedirs(path)
        print "Saving preprocessed rating data - %s" % (path + "/ratings.all")
        pickl.dump(R, open(path + "/ratings.all", "wb"))
        print "Done!"

        print "Saving preprocessed user info - %s" % (path + "/user_info.all")
        pickl.dump(user_info, open(path + "/user_info.all", "wb"))
        print "Done!"

        print "Saving preprocessed document data - %s" % (path + "/document.all")
        pickl.dump(D_all, open(path + "/document.all", "wb"))
        print "Done!"

        # print "Saving preprocessed user review data - %s" % (path + "/user_review.all")
        # pickl.dump(U_all, open(path + "/user_review.all", "wb"))
        # print "Done!"
        # print "Saving preprocessed movie review data - %s" % (path + "/movie_review.all")
        # pickl.dump(V_all, open(path + "/movie_review.all", "wb"))
        # print "Done!"

    def read_rating(self, path):
        results = []
        if os.path.isfile(path):
            raw_ratings = open(path, 'r')
        else:
            print "Path (preprocessed) is wrong!"
            sys.exit()
        index_list = []
        rating_list = []
        all_line = raw_ratings.read().splitlines()
        #data format is:  len i:r i:r

        for line in all_line:
            tmp = line.split()
            num_rating = int(tmp[0])
            if num_rating > 0:
                tmp_i, tmp_r = zip(*(elem.split(":") for elem in tmp[1::]))
                index_list.append(np.array(tmp_i, dtype=int))
                rating_list.append(np.array(tmp_r, dtype=float))
            else:
                index_list.append(np.array([], dtype=int))
                rating_list.append(np.array([], dtype=float))

        results.append(index_list)
        results.append(rating_list)

        return results

    def read_pretrained_word2vec(self, path, vocab, dim):
        if os.path.isfile(path):
            raw_word2vec = open(path, 'r')
        else:
            print "Path (word2vec) is wrong!"
            sys.exit()

        word2vec_dic = {}
        all_line = raw_word2vec.read().splitlines()
        mean = np.zeros(dim)
        count = 0
        for line in all_line:
            tmp = line.split()
            _word = tmp[0]
            _vec = np.array(tmp[1:], dtype=float)
            if _vec.shape[0] != dim:
                print "Mismatch the dimension of pre-trained word vector with word embedding dimension!"
                sys.exit()
            word2vec_dic[_word] = _vec
            mean = mean + _vec
            count = count + 1

        mean = mean / count

        W = np.zeros((len(vocab) + 1, dim))
        count = 0
        for _word, i in vocab:
            if word2vec_dic.has_key(_word):
                W[i + 1] = word2vec_dic[_word]
                count = count + 1
            else:
                W[i + 1] = np.random.normal(mean, 0.1, size=dim)

        print "%d words exist in the given pretrained model" % count

        return W

    def split_data(self, ratio, R):
        print "Randomly splitting rating data into training set (%.1f) and test set (%.1f)..." % (1 - ratio, ratio)
        train = []
        for i in xrange(R.shape[0]):            #R.shape[0]  the number of rows(also the number of users)
            user_rating = R[i].nonzero()[1]     #R[i].nonzero() is a list [user_idex,item_index];eg: [[0,0],[0,4]]
            np.random.shuffle(user_rating)      #user_rating is the i-th user click item's list
            train.append((i, user_rating[0]))   #tuple (i-th user_index,item_index); every user have a item;
        #print train
        remain_item = set(xrange(R.shape[1])) - set(zip(*train)[1])# zip(*train)[1] unzip train

        for j in remain_item:
            item_rating = R.tocsc().T[j].nonzero()[1]         #R.tocsc() according to column;
            np.random.shuffle(item_rating)
            train.append((item_rating[0], j))

        rating_list = set(zip(R.nonzero()[0], R.nonzero()[1]))
        total_size = len(rating_list)
        remain_rating_list = list(rating_list - set(train))
        random.shuffle(remain_rating_list)

        num_addition = int((1 - ratio) * total_size) - len(train)
        if num_addition < 0:
            print 'this ratio cannot be handled'
            sys.exit()
        else:
            train.extend(remain_rating_list[:num_addition])
            tmp_test = remain_rating_list[num_addition:]
            random.shuffle(tmp_test)
            valid = tmp_test[::2]
            test = tmp_test[1::2]

            trainset_u_idx, trainset_i_idx = zip(*train)
            trainset_u_idx = set(trainset_u_idx)
            trainset_i_idx = set(trainset_i_idx)
            if len(trainset_u_idx) != R.shape[0] or len(trainset_i_idx) != R.shape[1]:
                print "Fatal error in split function. Check your data again or contact authors"
                sys.exit()

        print "Finish constructing training set and test set"
        return train, valid, test

    def generate_train_valid_test_file_from_R(self, path, R, ratio):
        '''
        Split randomly rating matrix into training set, valid set and test set with given ratio (valid+test)
        and save three data sets to given path.
        Note that the training set contains at least a rating on every user and item.

        Input:
        - path: path to save training set, valid set, test set
        - R: rating matrix (csr_matrix)
        - ratio: (1-ratio), ratio/2 and ratio/2 of the entire dataset (R) will be training, valid and test set, respectively
        '''
        train, valid, test = self.split_data(ratio, R)
        print "Save training set and test set to %s..." % path
        if not os.path.exists(path):
            os.makedirs(path)

        R_lil = R.tolil() #R.todense()
        user_ratings_train = {}
        item_ratings_train = {}
        for i, j in train:
            if user_ratings_train.has_key(i):
                user_ratings_train[i].append(j)
            else:
                user_ratings_train[i] = [j]

            if item_ratings_train.has_key(j):
                item_ratings_train[j].append(i)
            else:
                item_ratings_train[j] = [i]

        user_ratings_valid = {}
        item_ratings_valid = {}
        for i, j in valid:
            if user_ratings_valid.has_key(i):
                user_ratings_valid[i].append(j)
            else:
                user_ratings_valid[i] = [j]

            if item_ratings_valid.has_key(j):
                item_ratings_valid[j].append(i)
            else:
                item_ratings_valid[j] = [i]

        user_ratings_test = {}
        item_ratings_test = {}
        for i, j in test:
            if user_ratings_test.has_key(i):
                user_ratings_test[i].append(j)
            else:
                user_ratings_test[i] = [j]

            if item_ratings_test.has_key(j):
                item_ratings_test[j].append(i)
            else:
                item_ratings_test[j] = [i]

        f_train_user = open(path + "/train_user.dat", "w")
        f_valid_user = open(path + "/valid_user.dat", "w")
        f_test_user = open(path + "/test_user.dat", "w")

        formatted_user_train = []
        formatted_user_valid = []
        formatted_user_test = []

        for i in xrange(R.shape[0]):
            if user_ratings_train.has_key(i):
                formatted = [str(len(user_ratings_train[i]))]#user's click counts of the item;
                formatted.extend(["%d:%.1f" % (j, R_lil[i, j])
                                  for j in sorted(user_ratings_train[i])])
                formatted_user_train.append(" ".join(formatted))#formatted_user_train format:  counts item_index:r1 item_index:r2 item_index:r3 ...
            else:
                formatted_user_train.append("0")

            if user_ratings_valid.has_key(i):
                formatted = [str(len(user_ratings_valid[i]))]
                formatted.extend(["%d:%.1f" % (j, R_lil[i, j])
                                  for j in sorted(user_ratings_valid[i])])
                formatted_user_valid.append(" ".join(formatted))
            else:
                formatted_user_valid.append("0")

            if user_ratings_test.has_key(i):
                formatted = [str(len(user_ratings_test[i]))]
                formatted.extend(["%d:%.1f" % (j, R_lil[i, j])
                                  for j in sorted(user_ratings_test[i])])
                formatted_user_test.append(" ".join(formatted))
            else:
                formatted_user_test.append("0")

        f_train_user.write("\n".join(formatted_user_train))
        f_valid_user.write("\n".join(formatted_user_valid))
        f_test_user.write("\n".join(formatted_user_test))

        f_train_user.close()
        f_valid_user.close()
        f_test_user.close()
        print "\ttrain_user.dat, valid_user.dat, test_user.dat files are generated."
        print "\torder by user_index, data format:  len(item) item1:rate1 item2:rate2 ...."
        f_train_item = open(path + "/train_item.dat", "w")
        f_valid_item = open(path + "/valid_item.dat", "w")
        f_test_item = open(path + "/test_item.dat", "w")

        formatted_item_train = []
        formatted_item_valid = []
        formatted_item_test = []

        for j in xrange(R.shape[1]):
            if item_ratings_train.has_key(j):
                formatted = [str(len(item_ratings_train[j]))]
                formatted.extend(["%d:%.1f" % (i, R_lil[i, j])
                                  for i in sorted(item_ratings_train[j])])
                formatted_item_train.append(" ".join(formatted))
            else:
                formatted_item_train.append("0")

            if item_ratings_valid.has_key(j):
                formatted = [str(len(item_ratings_valid[j]))]
                formatted.extend(["%d:%.1f" % (i, R_lil[i, j])
                                  for i in sorted(item_ratings_valid[j])])
                formatted_item_valid.append(" ".join(formatted))
            else:
                formatted_item_valid.append("0")

            if item_ratings_test.has_key(j):
                formatted = [str(len(item_ratings_test[j]))]
                formatted.extend(["%d:%.1f" % (i, R_lil[i, j])
                                  for i in sorted(item_ratings_test[j])])
                formatted_item_test.append(" ".join(formatted))
            else:
                formatted_item_test.append("0")

        f_train_item.write("\n".join(formatted_item_train))
        f_valid_item.write("\n".join(formatted_item_valid))
        f_test_item.write("\n".join(formatted_item_test))

        f_train_item.close()
        f_valid_item.close()
        f_test_item.close()
        print "\ttrain_item.dat, valid_item.dat, test_item.dat files are generated."
        print "\torder by item_index, data format:  len(user) user1:rate1 user2:rate2 ...."
        print "Done!"

    def generate_CTRCDLformat_content_file_from_D_all(self, path, D_all):
        '''
        Write word index with word count in document for CTR&CDL experiment

        '''
        f_text = open(path + "mult.dat", "w")
        X = D_all['X_base']
        formatted_text = []
        for i in xrange(X.shape[0]):
            word_count = sorted(set(X[i].nonzero()[1]))
            formatted = [str(len(word_count))]
            formatted.extend(["%d:%d" % (j, X[i, j]) for j in word_count])
            formatted_text.append(" ".join(formatted))

        f_text.write("\n".join(formatted_text))
        f_text.close()

    def preprocess(self, path_rating, path_itemtext, min_rating,
                   _max_length, _max_df, _vocab_size,path_user_review,path_movie_review,path_users_info):
        '''
        Preprocess rating and document data.

        Input:
            - path_rating: path for rating data (data format - user_id::item_id::rating)
            - path_itemtext: path for review or synopsis data (data format - item_id::text1|text2|text3|....)
            - path_user_review: path for review (data format - user_id::taxt1|text2|text3...)
            - path_movie_review: path for review (data format - movie_id::taxt1|text2|text3...)
            - min_rating: users who have less than "min_rating" ratings will be removed (default = 1)
            - _max_length: maximum length of document of each item (default = 300)
            - _max_df: terms will be ignored that have a document frequency higher than the given threshold (default = 0.5)
            - vocab_size: vocabulary size (default = 8000)

        Output:
            - R: rating matrix (csr_matrix: row - user, column - item)
            - D_all['X_sequence']: list of sequence of word index of each item ([[1,2,3,4,..],[2,3,4,...],...])
            - D_all['X_vocab']: list of tuple (word, index) in the given corpus
            - U_all
            - V_all
        '''
        # Validate data paths
        if os.path.isfile(path_rating):
            raw_ratings = open(path_rating, 'r')
            print "Path - rating data: %s" % path_rating
        else:
            print "Path(rating) is wrong!"
            sys.exit()

        if os.path.isfile(path_itemtext):
            raw_content = open(path_itemtext, 'r')
            print "Path - document data: %s" % path_itemtext
        else:
            print "Path(item text) is wrong!"
            sys.exit()
        '''
        if os.path.isfile(path_user_review):
            raw_user_review = open(path_user_review, 'r')
            print "Path - document data: %s" % path_user_review
        else:
            print "Path(user review text) is wrong!"
            sys.exit()
        if os.path.isfile(path_movie_review):
            raw_movie_review = open(path_movie_review, 'r')
            print "Path - document data: %s" % path_movie_review
        else:
            print "Path(movie review text) is wrong!"
            sys.exit()
        
        '''

        # 1st scan document file to filter items which have documents
        tmp_id_plot = set()
        all_line = raw_content.read().splitlines()
        for line in all_line:
            tmp = line.split('::')
            i = tmp[0]
            tmp_plot = tmp[1].split('|')
            if tmp_plot[0] == '':
                continue
            tmp_id_plot.add(i)
        raw_content.close()

        print "Preprocessing rating data..."
        print "\tCounting # ratings of each user and removing users having less than %d ratings..." % min_rating
        # 1st scan rating file to check # ratings of each user
        all_line = raw_ratings.read().splitlines()
        tmp_user = {}  #user rating counts;
        for line in all_line:
            tmp = line.split('::')
            u = tmp[0]
            i = tmp[1]
            if (i in tmp_id_plot):
                if (u not in tmp_user):
                    tmp_user[u] = 1
                else:
                    tmp_user[u] = tmp_user[u] + 1

        raw_ratings.close()

        # 2nd scan rating file to make matrix indices of users and items
        # with removing users and items which are not satisfied with the given
        # condition
        raw_ratings = open(path_rating, 'r')
        all_line = raw_ratings.read().splitlines()
        userset = {}
        itemset = {}
        user_idx = 0
        item_idx = 0

        user = []#id_index;0,1,2,...
        item = []#item_index;0,1,2,3,...
        rating = []#float ratings

        for line in all_line:
            tmp = line.split('::')
            u = tmp[0]
            if u not in tmp_user:#temp_user who  ratings;
                continue
            i = tmp[1]
            # An user will be skipped where the number of ratings of the user
            # is less than min_rating.
            if tmp_user[u] >= min_rating:
                if u not in userset:
                    userset[u] = user_idx
                    user_idx = user_idx + 1

                if (i not in itemset) and (i in tmp_id_plot):#tmp_id_plot item who have review info
                    itemset[i] = item_idx
                    item_idx = item_idx + 1
            else:
                continue

            if u in userset and i in itemset:
                u_idx = userset[u]
                i_idx = itemset[i]

                user.append(u_idx)
                item.append(i_idx)
                rating.append(float(tmp[2]))

        raw_ratings.close()

        R = csr_matrix((rating, (user, item)))
        #csr_matrix according rows;


        # mingfile =open("userIDS.txt","w")
        # for i in userset.keys():
        #     mingfile.write(str(i)+"\n")
        # mingfile.close()

        # mingfile=open("movieIDS.txt","w")
        # for i in itemset.keys():
        #     mingfile.write(str(i)+"\n")
        # mingfile.close()


        print "Finish preprocessing rating data - # user: %d, # item: %d, # ratings: %d" % (R.shape[0], R.shape[1], R.nnz)

         
        U_Info={}
        if  path_users_info:
            user_info=open(path_users_info,'r')
            all_line=user_info.read().splitlines()
            ages={'1':0,'18':1,'25':2,'35':3,'45':4,'50':5,'56':6}
            for line in all_line:
                tmp=line.split("::")#userid::gender::age::occupation::zipcode
                if tmp[0] not in userset:
                    continue
                ucode=[]
                if tmp[1]=='F':
                    ucode.append(0)
                    ucode.append(1)
                elif tmp[1]=='M':
                    ucode.append(1)
                    ucode.append(0)
                age_code=np.zeros(7)
                age_code[ages[tmp[2]]]=1
                ucode=ucode+age_code.tolist()
                occupation_code=np.zeros(21)
                occupation_code[int(tmp[3])]=1

                ucode=ucode+occupation_code.tolist()
                U_Info[tmp[0]]=ucode
            print "users info code is {}".format(len(U_Info.keys()))
            print U_Info[U_Info.keys()[0]]


        # 2nd scan document file to make idx2plot dictionary according to
        # indices of items in rating matrix
        print "Preprocessing item document..."

        # Read Document File
        raw_content = open(path_itemtext, 'r')
        max_length = _max_length
        map_idtoplot = {}
        all_line = raw_content.read().splitlines()
        for line in all_line:
            tmp = line.split('::')
            if tmp[0] in itemset:
                i = itemset[tmp[0]]
                tmp_plot = tmp[1].split('|')
                eachid_plot = (' '.join(tmp_plot)).split()[:max_length]
                map_idtoplot[i] = ' '.join(eachid_plot)

        print "\tRemoving stop words..."
        print "\tFiltering words by TF-IDF score with max_df: %.1f, vocab_size: %d" % (_max_df, _vocab_size)

        # Make vocabulary by document
        vectorizer = TfidfVectorizer(max_df=_max_df, stop_words={
                                     'english'}, max_features=_vocab_size)
        Raw_X = [map_idtoplot[i] for i in range(R.shape[1])]
        vectorizer.fit(Raw_X)
        vocab = vectorizer.vocabulary_
        X_vocab = sorted(vocab.items(), key=itemgetter(1))

        # Make input for run
        X_sequence = []
        for i in range(R.shape[1]):
            X_sequence.append(
                [vocab[word] + 1 for word in map_idtoplot[i].split() if vocab.has_key(word)])

        '''Make input for CTR & CDL'''
        baseline_vectorizer = CountVectorizer(vocabulary=vocab)
        X_base = baseline_vectorizer.fit_transform(Raw_X)

        D_all = {
            'X_sequence': X_sequence,
            'X_base': X_base,
            'X_vocab': X_vocab,
        }

        '''
        print "################################ start user review preprocess############################"
        # Read user review File
        raw_user_review = open(path_user_review, 'r')
        all_line=raw_user_review.read().splitlines()
        user_review_max_length=max([len([y.strip() for y in re.split('::|\|| ',x) if len(y)>1]) for x in all_line])

        print('The maximum length of all user review: {}'.format((user_review_max_length)))
        # vocab_processor = learn.preprocessing.VocabularyProcessor(user_review_max_length)
        user_review_vocab_size= _vocab_size
        map_idtoplot = {}
        for line in all_line:
            tmp = line.split('::')
            if tmp[0] in userset:
                i = userset[tmp[0]]
                tmp_plot =[ x.strip() for x in re.split('\|| ',tmp[1]) if len(y)>1]
                eachid_plot = (' '.join(tmp_plot)).split()[:user_review_max_length]
                map_idtoplot[i] = ' '.join(eachid_plot)

        print "\tRemoving stop words..."
        print len(map_idtoplot.keys())," ", (R.shape[0])
        Raw_U=[]
        for i in range(R.shape[0]):
            try:
                Raw_U.append(map_idtoplot[i])
            except  Exception as err:
                continue


        print "the length of user_review_vocab_size ",user_review_vocab_size
        print "\tFiltering words by TF-IDF score with max_df: %.1f, vocab_size: %d" % (_max_df, user_review_vocab_size)


        # Make vocabulary by document
        user_review_vectorizer = TfidfVectorizer(max_df=_max_df, stop_words={
                                     'english'}, max_features=user_review_vocab_size)

        user_review_vectorizer.fit(Raw_U)
        user_vocab = user_review_vectorizer.vocabulary_
        U_vocab = sorted(user_vocab.items(), key=itemgetter(1))

        # Make input for run
        U_sequence = []
        for i in range(R.shape[0]):
            tmp=[]
            try:
                for word in map_idtoplot[i].split():
                    if user_vocab.has_key(word):
                        tmp.append(user_vocab[word] + 1)
                U_sequence.append(tmp)
            except:
                continue



        #Make input for CTR & CDL
        baseline_vectorizer = CountVectorizer(vocabulary=user_vocab)
        U_base = baseline_vectorizer.fit_transform(Raw_U)

        U_all = {
            'U_sequence': U_sequence,
            'U_base': U_base,
            'U_vocab': U_vocab,
        }
        print "################################ end user review preprocess  ############################"

        print "################################ start movie review preprocess############################"
        # Read movie review File
        raw_movie_review = open(path_movie_review, 'r')
        all_line=raw_movie_review.read().splitlines()
        movie_review_max_length=max([len([y.strip() for y in re.split('::|\|| ',x) if len(y)>1]) for x in all_line])
        print('The maximum length of all user review: {}'.format((movie_review_max_length)))
        # vocab_processor = learn.preprocessing.VocabularyProcessor(movie_review_max_length)
        # movie_review_vocab_size=len(vocab_processor.vocabulary_)
        movie_review_vocab_size=_vocab_size

        map_idtoplot = {}
        for line in all_line:
            tmp = line.split('::')
            if tmp[0] in itemset:
                i = itemset[tmp[0]]
                # tmp_plot = tmp[1].split('|')
                tmp_plot =[ x.strip() for x in re.split('\|| ',tmp[1]) if len(y)>1]
                eachid_plot = (' '.join(tmp_plot)).split()[:movie_review_max_length]
                map_idtoplot[i] = ' '.join(eachid_plot)

        print "\tRemoving stop words..."
        print "\tFiltering words by TF-IDF score with max_df: %.1f, vocab_size: %d" % (_max_df, movie_review_vocab_size)

        # Make vocabulary by document
        movie_review_vectorizer = TfidfVectorizer(max_df=_max_df, stop_words={
                                     'english'}, max_features=movie_review_vocab_size)
        Raw_V = []

        for i in range(R.shape[1]):
            try:
                Raw_V.append(map_idtoplot[i])
            except  Exception as err:
                continue
        movie_review_vectorizer.fit(Raw_V)
        movie_vocab = movie_review_vectorizer.vocabulary_
        V_vocab = sorted(movie_vocab.items(), key=itemgetter(1))

        # Make input for run
        V_sequence = []
        for i in range(R.shape[1]):
            tmp=[]
            try:
                for word in map_idtoplot[i].split():
                    if movie_vocab.has_key(word):
                        tmp.append(movie_vocab[word] + 1)
                V_sequence.append(tmp)
            except:
                continue

        #Make input for CTR & CDL
        baseline_vectorizer = CountVectorizer(vocabulary=movie_vocab)
        V_base = baseline_vectorizer.fit_transform(Raw_V)

        V_all = {
            'U_sequence': V_sequence,
            'U_base': V_base,
            'U_vocab': V_vocab,
        }
        print "################################ end movie review preprocess  ############################"
        '''
        U_all={}
        V_all={}
        


        print "Finish preprocessing document data!"

        return R, D_all,U_all,V_all,U_Info

if __name__ == '__main__':
    data= Data_Factory()
    u=[0,0,1,1,2]
    v=[0,1,2,3,0]
    dt=[3,3,2,4,5]
    R=csr_matrix((dt,(u,v)))

    print  R.toarray()
    print "R0",R.shape[0]

    print "R1",R.shape[1]
    # print R[0].nonzero() 
    # print R.tolil()
    # print R[1].nonzero() 
    # print R[2].nonzero() 
    # print R[0]

    RR=R.copy().asfptype()


    for ix in range(R.shape[0]):
        print "user ",ix 
        r=[]
        temp=R[ix].nonzero()[1]
        ls= [R[ix,x] for x in  temp]
        print ls
        s=sum(ls)
        aver=s*1.0/len(temp)+0.1
        print aver,len(temp),s

        for x in temp:
            RR[ix,x]=float(R[ix,x])-aver

    print RR.toarray()
    print R.toarray()
    print R[0]
    print R[1]

    # items= np.array(R.shape[1])
    # for ix in range(R.shape[0]):










    # train = []
    # for i in xrange(R.shape[0]):            #R.shape[0]  the number of rows(also the number of users)
    #     user_rating = R[i].nonzero()[1]     #R[i].nonzero() is a list [user_idex,item_index];eg: [[0,0],[0,4]]
    #     np.random.shuffle(user_rating)      #user_rating is the i-th user click item's list
    #     train.append((i, user_rating[0]))   #tuple (i-th user_index,item_index); every user have a item;
    # print train
    # remain_item = set(xrange(R.shape[1])) - set(zip(*train)[1])# zip(*train)[1] unzip train
    # print zip(*train),";",zip(*train)[1]
    # print remain_item