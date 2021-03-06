# -*- coding: utf-8 -*-
from __future__ import unicode_literals
'''
Created on April 5, 2018

@author: ming
'''

import os
import time
import logging
from util import eval_RMSE_bias_list
import math
import numpy as np

def JONMF_P(train_user, train_item, valid_user, test_user,
           R, max_iter=50, lambda_u=1, lambda_v=100,lambda_q=10,lambda_p=10, dimension=50):
    # explicit setting
    a = 1
    b = 0
    eta=-0.0005
    alpha=1

    num_user = R.shape[0]
    num_item = R.shape[1]
    print "===================================ConvMF Models==================================="
    print "\tnum_user is:{}".format(num_user)
    print "\tnum_item is:{}".format(num_item)
    print "==================================================================================="
    PREV_LOSS = 1e-50

    Train_R_I = train_user[1] #this is rating; train_user_[0] is the item_index
    Train_R_J = train_item[1]
    Test_R = test_user[1]
    Valid_R = valid_user[1]

    # print train_user[1][0:5]

    '''
    compute the average of R
    '''

    train_sum=0
    test_sum=0
    valid_sum=0
    train_size=0
    test_size=0
    valid_size=0
    total_sum=0

    user_bias_sum=[]
    item_bias_sum=[]
    user_bias_size=[]
    item_bias_size=[]

   
    user_bias_dict=[]

    num_c=0
    for item in train_user[1]:
        train_sum=train_sum+ np.sum(item)
        train_size=train_size+np.size(item)

        user_bias_sum.append(np.sum(item))
        user_bias_size.append(len(item))
        item =item.tolist()
        i_index=[len(item)/4,len(item)/2,len(item)/4+len(item)/2]
        u_bias_list=[min(item),item[len(item)/4],item[len(item)/2],item[(int)(len(item)*0.75)],max(item)]
        user_bias_dict.append(u_bias_list)


    for item in test_user[1]:
        test_sum=test_sum+ np.sum(item)
        test_size=test_size+np.size(item)

    for item in valid_user[1]:
        valid_sum=valid_sum+ np.sum(item)
        valid_size=valid_size+np.size(item)

    for item in train_item[1]:
        item_bias_sum.append(np.sum(item))
        item_bias_size.append(len(item))


    total_size=train_size+test_size+valid_size
    total_sum=train_sum+test_sum+valid_sum
    global_average=total_sum*1.0/total_size

    user_bias=[user_bias_sum[i]/user_bias_size[i] for i in range(len(user_bias_sum))]
    item_bias=[item_bias_sum[i]/item_bias_size[i] for i in range(len(item_bias_sum))]
    print "######################################"
    print "sum: ",train_sum,test_sum,valid_sum
    print "size: ",train_size,test_size,valid_size
    print "average: ",train_sum*1.0/train_size, test_sum*1.0/test_size, valid_sum*1.0/valid_size
    print "global average: ",global_average
    print "user_bias:",  user_bias[0:50]
    print "item_bias:",   item_bias[0:50]
    print "######################################"
    '''
    prefrence matrix
    '''
    S_Train_R_I =[]# train_user[1]
    S_Train_R_J = []#train_item[1]
    S_Test_R = []#test_user[1]
    S_Valid_R = []#valid_user[1]

    uindx=0
    for item in train_user[1]:
        new_item=item.copy()
        inf=user_bias_dict[uindx][0]
        sup= user_bias_dict[uindx][4]
        a= sup-inf+1

        for i in range(len(item)):
            # if item[i] >user_bias[uindx] :      
            if item[i] >sup:
                new_item[i]=1.0     
            elif item[i] >inf :
                new_item[i]=(1.0+a *(sup-inf)**(-3))/(1+a*(item[i]-inf)**(-3))
                #1.0/(1.0+(item[i]-inf)**(-3))#1.0/(1.0+math.exp(-item[i]+user_bias[iidex]))
            else:
                new_item[i]=0
        S_Train_R_I.append(new_item)
        uindx=uindx+1
    S_Train_R_I=np.array(S_Train_R_I)

    uindx=0
    for item in train_item[1]:
        new_item=item.copy()
        for i in range(len(item)):
            temp_bias=train_item[0][uindx][i]
            
            inf= user_bias_dict[uindx][0]
            sup= user_bias_dict[uindx][4]
            a=sup-inf+1
            if item[i] > sup:
                new_item[i]=1.0
            elif item[i] >inf: #user_bias_dict[temp_bias][0] :#user_bias[temp_bias] :
                new_item[i]=(1.0+a *(sup-inf)**(-3))/(1+a*(item[i]-inf)**(-3))
                # new_item[i]= 1.0/(1.0+(item[i]-inf)**(-3))#1.0/(1.0+math.exp(-item[i]+user_bias[temp_bias]))
            else:
                new_item[i]=0
        S_Train_R_J.append(new_item)
        uindx=uindx+1
    S_Train_R_J=np.array(S_Train_R_J)

 
    pre_val_eval = 1e10


    stddv=1#1.0/np.sqrt(10)
    V = np.random.uniform(0.01,stddv,size=(num_item,dimension))
    U = np.random.uniform(0.01,stddv,size=(num_user, dimension))

    Q = np.random.uniform(0.01,stddv, size=(num_item,dimension))
    P = np.random.uniform(0.01,stddv,size=(num_user,dimension))
    M = np.random.uniform(0.01,stddv, size=(num_user,dimension))
    Gama=np.random.uniform(0.01,stddv, size=(dimension,dimension))

    endure_count = 100
    count = 0
    better_rmse=100
    better_mae =100
    for iteration in xrange(max_iter):
        
        loss = 0
        tic = time.time()
        print "%d iteration\t(patience: %d)" % (iteration, count)

        # VV = b * (V.T.dot(V)) + lambda_u * np.eye(dimension)#diagonal matrix
        sub_loss = np.zeros(num_user)
        print "=================================================================="
        print "the shape of U, U[i] {} {}".format(U.shape,U[0].shape)
        print "the shape of V, V[i] {} {}".format(V.shape,V[0].shape)
        print "=================================================================="
        for i in xrange(num_user):
            idx_item = train_user[0][i]
            #train_user[0]=[[item1,item2,item3...],[item1,itme3],[item3,item2]...]
            #train_user[1]=[[rating1,rating2,rating3...],[rating1,rating3],[rating2,rating5]...]
            V_i = V[idx_item]
            R_i = Train_R_I[i]#[rating1,rating2,rating3...]

            '''
            preference matrix
            '''
            Q_i = Q[idx_item]
            S_R_i = S_Train_R_I[i]
            S_approx_R_i=P[i].dot(Q_i.T)


            approx_R_i = U[i].dot(V_i.T)
            U_term1= (V_i*(np.tile(R_i, (dimension, 1)).T)).sum(0)#1*K
            U_term2= V_i.T.dot(V_i) #k*k
            U_term3= lambda_u*U[i]

            U_term1_Positive=0.5 * (np.abs(U_term1)+U_term1)
            U_term1_Negative =0.5 *(np.abs(U_term1)-U_term1)
            U_term2_Positive=0.5 * (np.abs(U_term2)+U_term2)
            U_term2_Negative =0.5 *(np.abs(U_term2)-U_term2)

            P_term1=(Q_i * (np.tile(S_R_i, (dimension, 1)).T)).sum(0)
            P_term2=Q_i.T.dot(Q_i)
            P_term3=lambda_p*P[i]

            P_term1_Positive=0.5*(np.abs(P_term1)+P_term1)
            P_term1_Negative= 0.5*(np.abs(P_term1)-P_term1)
            P_term2_Positive=0.5*(np.abs(P_term2)+P_term2)
            P_term2_Negative= 0.5*(np.abs(P_term2)-P_term2)
            U[i]=U[i]*np.sqrt((U_term1_Positive+U[i].dot(U_term2_Negative)+M[i])/(U_term1_Negative+U[i].dot(U_term2_Positive)+(1+lambda_u)*U[i]))
            P[i]=P[i]*(np.sqrt((P_term1_Positive+P[i].dot(P_term2_Negative)+M[i])/(P_term1_Negative+P[i].dot(P_term2_Positive)+(1+lambda_p)*P[i])))

            M_term=M[i].dot(Gama)
            M_term_Positive=0.5*(np.abs(M_term)+M_term)
            M_term_Negative=0.5*(np.abs(M_term)-M_term)
            M[i]=M[i]*np.sqrt((U[i]+P[i]+M_term_Negative)/(2*M[i]+M_term_Positive))

            sub_loss[i] =sub_loss[i] -0.5 * lambda_u * np.dot(U[i], U[i])
            sub_loss[i] =sub_loss[i]-0.5 * lambda_p * np.dot(P[i], P[i])


        Gama=M.T.dot(U)+M.T.dot(P)-2*np.eye(dimension)
        loss = loss + np.sum(sub_loss)
        loss=loss-np.sum(np.square(M))
        print "=================================================================="
        print "the shape of V, V[i] {} {}".format(V.shape,V[0].shape)
        print "the loss of U is {}".format(np.sum(np.square(U)))
        print "the loss of M is {}".format(np.sum(np.square(M)))
        print "=================================================================="
        sub_loss = np.zeros(num_item)
        # UU = b * (U.T.dot(U))
        # SUU = b *(P.T.dot(P))
        for j in xrange(num_item):
            idx_user = train_item[0][j]
            U_j = U[idx_user]
            R_j = Train_R_J[j]

            A = (a - b) * (U_j.T.dot(U_j))
            B = (a * U_j * (np.tile(R_j, (dimension, 1)).T)).sum(0)
            approx_R_j = U_j.dot(V[j].T)
            # V[j]=V[j]+eta*((U_j * (np.tile(-R_j+approx_R_j, (dimension, 1)).T)).sum(0)+lambda_v*V[j])
            m_temp=A+lambda_v * np.eye(dimension)
            # try:
            #     ming_test=np.linalg.cholesky(m_temp)
            # except Exception as err:
            #     print err
            #     print "UU+lambda_v*E  is not a positive matix"
         
            V[j]= (np.linalg.solve(m_temp.T, B.T)).T
            sub_loss[j] = -0.5 * lambda_v * np.dot(V[j], V[j])

            temp_loss=-0.5 * np.square(R_j * a).sum()
            temp_loss=temp_loss+a * np.sum((U_j.dot(V[j])) * R_j)
            temp_loss=temp_loss - 0.5 * np.dot(V[j].dot(A), V[j])

            sub_loss[j]=sub_loss[j]+temp_loss

            '''
            preference Matrix
            '''
            S_R_j = S_Train_R_J[j]
            P_j = P[idx_user]

            SA = (a - b) * (P_j.T.dot(P_j))
            SB = (a * P_j * (np.tile(S_R_j, (dimension, 1)).T)).sum(0)

            S_approx_R_j = P_j.dot(Q[j].T)
            # Q[j]=Q[j]+eta*((P_j * (np.tile(-S_R_j+S_approx_R_j, (dimension, 1)).T)).sum(0)+lambda_q*Q[j])
            m_temp=SA+lambda_q * np.eye(dimension)
            # try:
            #     ming_test=np.linalg.cholesky(m_temp)
            # except Exception as err:
            #     print err
            #     print "PP+lambda_q*E  is not a positive matix"

            Q[j] = (np.linalg.solve(m_temp.T, SB.T)).T #A*X=B  X =A^-1*B


            sub_loss[j] =sub_loss[j] -0.5 * lambda_q * np.dot(Q[j], Q[j])

            temp_loss=-0.5 * np.square(S_R_j * a).sum()
            temp_loss=temp_loss+a * np.sum((P_j.dot(Q[j])) * S_R_j)
            temp_loss=temp_loss - 0.5 * np.dot(Q[j].dot(SA), Q[j])

            sub_loss[j] = sub_loss[j] + temp_loss#(1-alpha)*
        loss =loss + np.sum(sub_loss)
        seed = np.random.randint(100000)

        topk=[3,5,10,15,20,25,30,40,50,100]
     
        tr_eval,tr_recall,tr_mae,tr_ndcg=eval_RMSE_bias_list(train_user[1], U, V, train_user[0],topk,user_bias)
        val_eval,va_recall,va_mae,val_ndcg = eval_RMSE_bias_list(valid_user[1], U, V, valid_user[0],topk,user_bias)
        te_eval,te_recall,te_mae,te_ndcg = eval_RMSE_bias_list(test_user[1], U, V, test_user[0],topk,user_bias)
        for i in range(len(topk)):
            print "recall top-{}: Train:{} Validation:{}  Test:{}".format(topk[i],tr_recall[i],va_recall[i],te_recall[i])
        
        print "ndcg train {}, val {}, test {}".format(tr_ndcg,val_ndcg,te_ndcg)


        toc = time.time()
        elapsed = toc - tic
        converge = abs((loss - PREV_LOSS) / PREV_LOSS)

        if (val_eval < pre_val_eval):
            print "Best Test result!!!!!"
        else:
            count = count + 1
        pre_val_eval = val_eval
        print "JONMF_P=====================RMSE============================="
        print "Loss: %.5f Elpased: %.4fs Converge: %.6f Train: %.5f Validation: %.5f Test: %.5f" % (
            loss, elapsed, converge, tr_eval, val_eval, te_eval)
        print "JONMF_P=====================MAE============================="
        print " Train: %.5f Validation: %.5f Test: %.5f" % ( tr_mae, va_mae, te_mae)
        if te_eval <better_rmse:
            better_rmse=te_eval
        if te_mae < better_mae:
            better_mae = te_mae
        print "\n JONMF_P========better_rmse:{}   better_mae:{}==========\n".format(better_rmse,better_mae)

        if (count == endure_count):
            break
        PREV_LOSS = loss
