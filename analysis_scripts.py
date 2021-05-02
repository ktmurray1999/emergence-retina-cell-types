# -*- coding: utf-8 -*-
"""
Created on Thu Apr  8 17:36:09 2021

@author: Keith
"""

import torch
import torch.nn as nn
import shutil
import matplotlib.pyplot as plt
from retina_model import Bipolar, Amacrine, Ganglion, AnalysisModel, TestModel, Dataset, CompareTensors, reConfigure, TestModel_LeftRight
from create_data import createDataTest, plotStimulus, tens_np, createSet_definedDist
from truncated_models import TransplantModel, TransplantModel_TopDist, TransplantModel_TopDist_SanAma
import random
import itertools
import numpy as np
import json

device = torch.device("cuda:0")

def PsychometricCurveAnalysis(types,model):
    net = AnalysisModel(types, 0.00).to(device)
    save_loc = 'Q:\Documents\TDS SuperUROP\\'+model+'.pt'
    weights = torch.load(save_loc)
    net.load_state_dict(weights)
    net.eval()
    
    results = []
    
    for x in range(0,41):
        createDataTest('psychometric' , x/10, 0, 100)
        accuracy = TestModel(net, 'testset_psychometric', 100)
        results.append(accuracy)
        shutil.rmtree('Q:/Documents/TDS SuperUROP/testset_psychometric')
        
    for x in range(0,41):
        if x < 10:
            results[x] = 1 - results[x]
        
    fig = plt.figure()
    ax = plt.axes()
    ax.plot([x/10 for x in range(0,41)], results)
    
    plt.xlabel('Ratio between Velocities')
    plt.ylabel('Accuracy')
    plt.title('Model accuracy in varied environments')
    plt.show()
    return results
    

def FindRelevantTypes(types, model, testset, threshold, exist=None):
    if exist is None:
        net = AnalysisModel(types, 0.00).to(device)
        save_loc = 'Q:\Documents\TDS SuperUROP\\'+model+'.pt'
        weights = torch.load(save_loc)
        net.load_state_dict(weights)
    else:
        net = exist
        state = net.state_dict()
    net.eval()
    
    base_result, label_dists = TestModel(net, testset, 100, label_dis=True)
    base_result = base_result.item()
    print(base_result)
    resultsB = []
    resultsA = []
    resultsG = []
    
    for i in net.children():
        if isinstance(i, Bipolar):
            temp_weight = i.bipolar_temporal.weight.data
            temp_bias = i.bipolar_temporal.bias.data
            i.bipolar_temporal.weight.data = torch.zeros(temp_weight.shape).to(device)
            i.bipolar_temporal.bias.data = torch.zeros(temp_bias.shape).to(device)
            accuracy = TestModel(net, testset, 100).item()
            resultsB.append(accuracy)
            if accuracy < threshold*base_result:
                i.bipolar_temporal.weight.data = temp_weight
                i.bipolar_temporal.bias.data = temp_bias
        
        elif isinstance(i, Amacrine):
            temp_weight = i.amacrine_temporal.weight.data
            temp_bias = i.amacrine_temporal.bias.data
            i.amacrine_temporal.weight.data = torch.zeros(temp_weight.shape).to(device)
            i.amacrine_temporal.bias.data = torch.zeros(temp_bias.shape).to(device)
            accuracy = TestModel(net, testset, 100).item()
            resultsA.append(accuracy)
            if accuracy < threshold*base_result:
                i.amacrine_temporal.weight.data = temp_weight
                i.amacrine_temporal.bias.data = temp_bias
            
        elif isinstance(i, Ganglion):
            temp_weight = i.ganglion_temporal.weight.data
            temp_bias = i.ganglion_temporal.bias.data
            i.ganglion_temporal.weight.data = torch.zeros(temp_weight.shape).to(device)
            i.ganglion_temporal.bias.data = torch.zeros(temp_bias.shape).to(device)
            accuracy = TestModel(net, testset, 100).item()
            resultsG.append(accuracy)
            if accuracy < threshold*base_result:
                i.ganglion_temporal.weight.data = temp_weight
                i.ganglion_temporal.bias.data = temp_bias

    fig = plt.figure()
    ax = plt.axes()
    ax.plot(resultsB, 'y')
    ax.plot(resultsA, 'r')
    ax.plot(resultsG, 'g')
    ax.plot([threshold*base_result for i in range(len(resultsB))], 'p-')
    ax.plot([label_dists[0].item() for i in range(len(resultsB))], 'm+')
    ax.plot([label_dists[1].item() for i in range(len(resultsB))], 'k+')

    plt.xlabel('Cell Type Leissioned')
    plt.ylabel('Accuracy')
    plt.title('Leissioning Cell Types to Affect Accuracy')
    plt.show()
    
    if exist is not None:
        net.load_state_dict(state)
    return [resultsB, resultsA, resultsG]


def scramble(net):
    net_list = list(net.children())
    random.shuffle(net_list)
    return net_list


def PruneNonImportantCells(types, model, testset, threshold, graph=True):
    net = AnalysisModel(types, 0.00).to(device)
    save_loc = 'Q:\Documents\TDS SuperUROP\\'+model+'.pt'
    weights = torch.load(save_loc)
    net.load_state_dict(weights)
    net.eval()
    
    base_result = TestModel(net, testset, 100, printTF=False).item()
    resultsB = []
    resultsA = []
    resultsG = []
    cells_kept = 0
    
    for i in scramble(net):
        if isinstance(i, Ganglion):
            temp_weight = i.ganglion_temporal.weight.data
            i.ganglion_temporal.weight.data = torch.zeros(temp_weight.shape).to(device)
            accuracy = TestModel(net, testset, 100).item()
            resultsG.append(accuracy)
            if accuracy < threshold*base_result:
                i.ganglion_temporal.weight.data = temp_weight
                cells_kept += 1
            
    for i in scramble(net):
        if isinstance(i, Bipolar):
            temp_weight = i.bipolar_temporal.weight.data
            i.bipolar_temporal.weight.data = torch.zeros(temp_weight.shape).to(device)
            accuracy = TestModel(net, testset, 100).item()
            resultsB.append(accuracy)
            if accuracy < threshold*base_result:
                i.bipolar_temporal.weight.data = temp_weight
                cells_kept += 1
        
    for i in scramble(net):
        if isinstance(i, Amacrine):
            temp_weight = i.amacrine_temporal.weight.data
            i.amacrine_temporal.weight.data = torch.zeros(temp_weight.shape).to(device)
            accuracy = TestModel(net, testset, 100).item()
            resultsA.append(accuracy)
            if accuracy < threshold*base_result:
                i.amacrine_temporal.weight.data = temp_weight
                cells_kept += 1
    
    print('Cells Kept: '+str(cells_kept))
    
    if graph:
        fig = plt.figure()
        ax = plt.axes()
        ax.plot(resultsB, 'y')
        ax.plot(resultsA, 'r')
        ax.plot(resultsG, 'g')
        ax.plot([threshold*base_result for i in range(len(resultsB))], 'p-')
        
        plt.xlabel('Cell Type Leissioned')
        plt.ylabel('Accuracy')
        plt.title('Continual Leissioning Cell Types to Affect Accuracy')
        plt.show()
    return (net, cells_kept)


def PrinciplePrune(types, model, testset):
    net = AnalysisModel(types, 0.00).to(device)
    save_loc = 'Q:\Documents\TDS SuperUROP\\'+model+'.pt'
    weights = torch.load(save_loc)
    net.load_state_dict(weights)
    net.eval()
    
    high_score = 0.90
    best_set = None
    
    basket1 = ['0','1','2','3','4','5','6','7']
    basket2 = ['0','1','2','3','4','5','6','7']
    basket3 = ['0','1','2','3','4','5','6','7']
    basket4 = ['1','2','4','6','7']
    basket5 = ['0','2','3','6','7']
    basket6 = ['0','2','3']
    
    for i in range(len(basket1)):
        basket1[i] = 'bipolar' + basket1[i]
        basket2[i] = 'amacrine' + basket2[i]
        basket3[i] = 'ganglion' + basket3[i]
    for i in range(len(basket4)):
        basket4[i] = 'bipolar' + basket4[i]
    for i in range(len(basket5)):
        basket5[i] = 'amacrine' + basket5[i]
    for i in range(len(basket6)):
        basket6[i] = 'ganglion' + basket6[i]

    baskets = set(basket1 + basket2 + basket3)
    x = list(itertools.combinations(basket4, 1)) + list(itertools.combinations(basket4, 2))
    y = list(itertools.combinations(basket5, 1)) + list(itertools.combinations(basket5, 2))
    z = list(itertools.combinations(basket6[:2], 2)) + list(itertools.combinations(basket6, 3))
    
    for a in x:
        for b in y:
            for c in z:
                temp_set = set(a + b + c)
                exclude = baskets - temp_set
                for i in exclude:
                    if 'bipolar' in i:
                        exec("""
net.{0}.bipolar_temporal.weight.data = torch.zeros(1, 1, 31, 1, 1).to(device)
net.{0}.bipolar_temporal.bias.data = torch.zeros(1).to(device)
                         """.format(i))                    
                    elif 'amacrine' in i:
                        exec("""
net.{0}.amacrine_temporal.weight.data = torch.zeros(1, 1, 31, 1, 1).to(device)
net.{0}.amacrine_temporal.bias.data = torch.zeros(1).to(device)
                         """.format(i))
                    elif 'ganglion' in i:
                        exec("""
net.{0}.ganglion_temporal.weight.data = torch.zeros(1, 1, 31, 1, 1).to(device)
net.{0}.ganglion_temporal.bias.data = torch.zeros(1).to(device)
                         """.format(i))
                
                accuracy = TestModel(net, testset, 100).item()
                if accuracy > high_score:
                    # high_score = accuracy
                    # best_set = temp_set
                    print(accuracy)
                    print(temp_set)
                elif accuracy > 0.80 and accuracy == high_score:
                    print(accuracy)
                    print(temp_set)
                
                net.load_state_dict(weights)
                net.eval()
    
    return best_set, high_score


def CreateLeisionGraph():
    leision_results = []
    for x in range(75,101):
        temp_results = []
        for i in range(4):
            (net, cells_kept) = PruneNonImportantCells(8, 'model\\model', 'testset_2x_speed', x/100, graph=False)
            temp_results.append(cells_kept)
        leision_results.append(sum(temp_results)/len(temp_results))
        
    fig = plt.figure()
    ax = plt.axes()
    ax.plot([x/100 for x in range(75,101)], leision_results)
    plt.xlabel('Accuracy Threshold')
    plt.ylabel('Number of Cells Kept')
    plt.title('The amount of cells necessary to maintain various accuracies')
    plt.show()


class DreamMap(nn.Module):
    def __init__(self):
        super(DreamMap, self).__init__()
        self.map = nn.parameter.Parameter(torch.rand(1,1,31,255,255)*2-1)
        self.drop = nn.Dropout(p=0.10)
        self.clip = nn.Tanh()

    def forward(self):
        fin = self.clip(self.drop(self.map))
        return fin


def TrainDeepDream(types, model, dream, epochs, iterations):
    # Create Model
    net = AnalysisModel(types, 0.00).to(device)
    save_loc = 'Q:\Documents\TDS SuperUROP\\'+model+'.pt'
    weights = torch.load(save_loc)
    net.load_state_dict(weights)
    net.eval()
    
    # Optimize and Loss
    dream.train()
    optimizer = torch.optim.Adam(dream.parameters(), weight_decay=0.00001)
    res = []
    
    # Train
    for epoch in range(epochs):
        dream.train()
        for r in range(iterations):
            optimizer.zero_grad()
            inputs = dream()
            outputs = net.deepdream(inputs)
            outputs.backward(retain_graph=True)
            optimizer.step()
            res.append(outputs.item())
            
    plt.plot(res)
    dream.eval()
    print('Finished Training')


def DifferentStages(types, model, testset, num, stim=None):
    net = AnalysisModel(types, 0.00).to(device)
    save_loc = 'Q:\Documents\TDS SuperUROP\\'+model+'.pt'
    weights = torch.load(save_loc)
    net.load_state_dict(weights)
    net.eval()
    
    if stim is None:
        stimulus = torch.load('Q:/Documents/TDS SuperUROP/'+ testset +'/'+num+'/stimulus.pt').to(device)
    else:
        stimulus = stim
    
    bipolar_outputs, amacrine_outputs, ganglion_outputs, dcsnLeft, dcsnRight = net.extractstage(stimulus)
    
    for i in range(types):
        plotStimulus(bipolar_outputs[i], 'bipolar'+str(i))
        plotStimulus(amacrine_outputs[i], 'amacrine'+str(i))
        plotStimulus(ganglion_outputs[i], 'ganglion'+str(i))
        # fig = plt.figure()
        # ax = plt.axes()
        # ax.plot(tens_np(torch.flatten(ganglion_outputs[i][0,0],start_dim=1))[:,:10])
        # plt.show()
    
    fig = plt.figure()
    ax = plt.axes()
    ax.plot(tens_np(torch.squeeze(dcsnLeft)), 'r', label='Left Cell')
    ax.plot(tens_np(torch.squeeze(dcsnRight)), 'g', label='Right Cell')
    plt.xlabel('Time Step')
    plt.ylabel('Response')
    plt.title('Right and Left Cell Responses')
    plt.legend()
    plt.show()


def TestFlaws(types, model, data, label, printTF=False):
    # Model
    net = AnalysisModel(types, 0.00).to(device)
    save_loc = 'Q:\Documents\TDS SuperUROP\\'+model+'.pt'
    weights = torch.load(save_loc)
    net.load_state_dict(weights)
    net.eval()
    
    # Datasets
    testfunc = Dataset(data,range(label))
    testloader = torch.utils.data.DataLoader(testfunc, batch_size=1, shuffle=False, num_workers=0)
    
    # Test    
    running_loss = 0
    for i, data in enumerate(testloader, 0):
        inputs, labels = torch.unsqueeze(torch.unsqueeze(torch.squeeze(data[0].to(device)), dim=0), dim=0), data[1].to(device)
        outputs = net(inputs)
        comparison = CompareTensors(outputs, labels)
        if comparison == 0:
            plotStimulus(inputs, 'wrong_in'+str(i))
        running_loss += comparison
        
    if printTF:
        print('Acuracy: %.2f' % (running_loss/label))
    return running_loss/label


def SlowVelocityTest(types,model):
    net = AnalysisModel(types, 0.00).to(device)
    save_loc = 'Q:\Documents\TDS SuperUROP\\'+model+'.pt'
    weights = torch.load(save_loc)
    net.load_state_dict(weights)
    net.eval()
    
    results = []
    
    for x in range(0,41):
        createDataTest('slow_velocity', 2, 0, 100, slow_speed=x/10)
        accuracy = TestModel(net, 'testset_slow_velocity', 100)
        results.append(accuracy)
        shutil.rmtree('Q:/Documents/TDS SuperUROP/testset_slow_velocity')
        
    fig = plt.figure()
    ax = plt.axes()
    ax.plot([x/10 for x in range(0,41)], results)
    
    plt.xlabel('Slow Velocity')
    plt.ylabel('Accuracy')
    plt.title('Accuracy of Model across various Slow Velocities')
    plt.show()
    return results


def ExtractStageActivations(net, data, label):    
    # Datasets
    testfunc = Dataset(data,range(label))
    testloader = torch.utils.data.DataLoader(testfunc, batch_size=label, shuffle=False, num_workers=0)
    
    stage_result = []
    
    # Test
    for i, data in enumerate(testloader, 0):
        inputs, labels = reConfigure(data)
        bipolar_outputs, amacrine_outputs, ganglion_outputs, dcsnLeft, dcsnRight = net.extractstage(inputs)
        
        for j in range(len(bipolar_outputs)):
            stage_result.append(torch.mean(bipolar_outputs[j]).item())
        for j in range(len(bipolar_outputs)):
            stage_result.append(torch.mean(amacrine_outputs[j]).item())
        for j in range(len(bipolar_outputs)):
            stage_result.append(torch.mean(ganglion_outputs[j]).item())
        break
    
    return stage_result


def ResponsesAcrossDifferentStages(types, model):
    net = AnalysisModel(types, 0.00).to(device)
    save_loc = 'Q:\Documents\TDS SuperUROP\\'+model+'.pt'
    weights = torch.load(save_loc)
    net.load_state_dict(weights)
    net.eval()
    
    all_stage_activations = []
    
    for x in range(5,21):
        createDataTest('slow_velocity', 2, 0, 50, slow_speed=x/10)
        stage_activities = ExtractStageActivations(net, 'testset_slow_velocity', 50)
        all_stage_activations.append(stage_activities)
        shutil.rmtree('Q:/Documents/TDS SuperUROP/testset_slow_velocity')
    
    results = np.array(all_stage_activations).T
    count = 0
    
    for x in ['Bipolar','Amacrine','Ganglion']:
        fig = plt.figure()
        ax = plt.axes()
        for y in range(types):
            ax.plot([x/10 for x in range(5,21)],results[count, :], label=str(y))
            count += 1
        plt.xlabel('Slow Velocity')
        plt.ylabel('Average Response Magnitude')
        plt.title(x+' Type Average Response Magnitude across Slow Velocities')
        plt.legend()
        plt.show()
    
    return results


def BottomDist():
    return np.random.random_sample()/8 + 0.55


def LowerDist():
    return np.random.random_sample()/4 + 0.5


def UpperDist():
    return 3*np.random.random_sample()/4 + 0.75


def TopDist():
    return np.random.random_sample()/2 + 1


def MakeVaryingDists():
    createSet_definedDist('testset_bottom_dist',100,2,BottomDist)
    createSet_definedDist('testset_lower_dist',100,2,LowerDist)
    createSet_definedDist('testset_upper_dist',100,2,UpperDist)
    createSet_definedDist('testset_top_dist',100,2,TopDist)


def TruncateModelBarLesion(types, model, testset):
    net = AnalysisModel(types, 0.00).to(device)
    save_loc = 'Q:\Documents\TDS SuperUROP\\'+model+'.pt'
    weights = torch.load(save_loc)
    net.load_state_dict(weights)
    net.eval()
    
    base_res, true_left, true_right = TestModel_LeftRight(net, testset, 100)
    base_result = base_res
    print(base_result)
    resultsB = None
    resultsA = None
    resultsG0 = None
    resultsG2 = None
    
    for i in net.children():
        if isinstance(i, Bipolar):
            temp_weight = i.bipolar_temporal.weight.data
            temp_bias = i.bipolar_temporal.bias.data
            i.bipolar_temporal.weight.data = torch.zeros(temp_weight.shape).to(device)
            i.bipolar_temporal.bias.data = torch.zeros(temp_bias.shape).to(device)
            accuracy, left, right = TestModel_LeftRight(net, testset, 100)
            if accuracy < base_result:
                resultsB = (accuracy, left, right)
                i.bipolar_temporal.weight.data = temp_weight
                i.bipolar_temporal.bias.data = temp_bias
        
        elif isinstance(i, Amacrine):
            temp_weight = i.amacrine_temporal.weight.data
            temp_bias = i.amacrine_temporal.bias.data
            i.amacrine_temporal.weight.data = torch.zeros(temp_weight.shape).to(device)
            i.amacrine_temporal.bias.data = torch.zeros(temp_bias.shape).to(device)
            accuracy, left, right = TestModel_LeftRight(net, testset, 100)
            if accuracy < base_result:
                resultsA = (accuracy, left, right)
                i.amacrine_temporal.weight.data = temp_weight
                i.amacrine_temporal.bias.data = temp_bias
            
        elif isinstance(i, Ganglion):
            temp_weight = i.ganglion_temporal.weight.data
            temp_bias = i.ganglion_temporal.bias.data
            i.ganglion_temporal.weight.data = torch.zeros(temp_weight.shape).to(device)
            i.ganglion_temporal.bias.data = torch.zeros(temp_bias.shape).to(device)
            accuracy, left, right = TestModel_LeftRight(net, testset, 100)
            if accuracy < base_result:
                if resultsG0 is None:
                    resultsG0 = (accuracy, left, right)
                else:
                    resultsG2 = (accuracy, left, right)
                i.ganglion_temporal.weight.data = temp_weight
                i.ganglion_temporal.bias.data = temp_bias
                
    left_accuracy = [base_res*true_left, resultsB[0]*resultsB[1], resultsA[0]*resultsA[1], resultsG0[0]*resultsG0[1], resultsG2[0]*resultsG2[1]]
    right_accuracy = [base_res*true_right, resultsB[0]*resultsB[2], resultsA[0]*resultsA[2], resultsG0[0]*resultsG0[2], resultsG2[0]*resultsG2[2]]
    
    X = ['Full Model','Bipolar Lesion', 'Amacrine Lesion', 'Ganglion1 Lesion', 'Ganglion2 Lesion']
    fig = plt.figure()
    ax = fig.add_axes([0,0,1,1])
    ax.bar(X, left_accuracy, color = 'c', width = 0.25, label='Left Direction Accuracy')
    ax.bar(X, right_accuracy, bottom=left_accuracy, color = 'm', width = 0.25, label='Right Direction Accuracy')
    plt.ylabel('Model Accuracy Percentage')
    plt.title('Accuracy when lesioning various cells')
    plt.legend()
    plt.savefig('Q:/Documents/TDS SuperUROP/truncated_model_lesion.svg')
    plt.show()


def ExamineAmacrineResponsesinTruncated(types, cell, testset):
    left_accuracy = []
    right_accuracy = []
    
    for i in range(8):
        net = AnalysisModel(types, 0.00).to(device)
        save_loc = 'Q:\Documents\TDS SuperUROP\\model\\'+cell+'\\model_top_dist_'+str(i)+'.pt'
        weights = torch.load(save_loc)
        net.load_state_dict(weights)
        net.eval()
        base_res, true_left, true_right = TestModel_LeftRight(net, testset, 100)
        left_accuracy.append(base_res*true_left)
        right_accuracy.append(base_res*true_right)

    X = [x for x in range(8)]
    fig = plt.figure()
    ax = fig.add_axes([0,0,1,1])
    ax.bar(X, left_accuracy, color = 'c', width = 0.25, label='Left Direction Accuracy')
    ax.bar(X, right_accuracy, bottom=left_accuracy, color = 'm', width = 0.25, label='Right Direction Accuracy')
    plt.ylabel('Model Accuracy Percentage')
    plt.xlabel(cell+' Cell')
    plt.title('Accuracy when using different '+cell+' Cells')
    plt.legend()
    plt.savefig('Q:/Documents/TDS SuperUROP\\'+cell+'_substitute.svg')
    plt.show()


def TestsetVelocityDist():
    for x in range(0,34):
        speed = 0.50 + x*.03
        createDataTest('2x_'+str(x)+'_dist', 2, 0, 100, slow_speed=speed)
        print(speed)
    return None


def BipolarAmacrineSubstitute():
    model_results = {}
    bipolar = [1,2,4,6,7]
    amacrine = [0,2,3,6,7]
    for b in bipolar:
        for a in amacrine:
            left_accuracy = []
            right_accuracy = []
            net = AnalysisModel(2, 0.00).to(device)
            save_loc = 'Q:\Documents\TDS SuperUROP\\model\\combinations\\model_'+str(b)+'_'+str(a)+'.pt'
            weights = torch.load(save_loc)
            net.load_state_dict(weights)
            net.eval()
            
            for i in range(0,34):
                testset = 'testset_2x_'+str(i)+'_dist'
                base_res, left, right = TestModel_LeftRight(net, testset, 100)
                left = base_res*left
                right = base_res*right
                left_accuracy.append(left.item())
                right_accuracy.append(right.item())
                
            model_results[str(b)+'_'+str(a)] = [left_accuracy, right_accuracy]
            current_results = {'Left Accuracy': left_accuracy, 'Right Accuracy': right_accuracy}
            velocity_labels = [x*0.03 + 0.50 for x in range(0,34)]
            
            fig, ax = plt.subplots()
            ax.stackplot(velocity_labels, current_results.values(),
                         labels=current_results.keys())
            ax.legend(loc='upper left')
            ax.set_title('Slow Velocity Curve for Bipolar '+str(b) + ' and Amacrine '+str(a))
            ax.set_xlabel('Slow Velocity')
            ax.set_ylabel('Model Accuracy')
            plt.savefig('Q:/Documents/TDS SuperUROP\\model\\combination_graphs\\graph_'+str(b)+'_'+str(a)+'.svg')
            plt.show()    

    # json_dump = json.dumps(model_results)
    # f = open("Q:/Documents/TDS SuperUROP\\model\\combinations.json","w")
    # f.write(json_dump)
    # f.close()
    return model_results


if __name__ == "__main__":
    
    # results = PsychometricCurveAnalysis(8,'model_2x')
    # results = FindRelevantTypes(8, 'model\\model', 'testset_2x_speed', 1.01)
    # results = FindRelevantTypes(8, 'model\\model', 'testset_2x_speed', 1.00)
    # results = FindRelevantTypes(8, 'model\\model', 'testset_2x_speed', 0.95)
    # results = FindRelevantTypes(8, 'model\\model', 'testset_2x_speed', 0.90)
    
    # CreateLeisionGraph()
    # SlowVelocityTest(8, 'model\\model')
    # ResponsesAcrossDifferentStages(8, 'model\\model')
    # best_set, high_score = PrinciplePrune(8, 'model\\model', 'testset_2x_speed')
    
    # TransplantModel()
    # results = FindRelevantTypes(2, 'model\\model_2_types', 'testset_2x_speed', 1.00, exist=None)
    # PsychometricCurveAnalysis(2, 'model\\model_2_types')
    
    # plotStimulus(torch.load('Q:/Documents/TDS SuperUROP/testset_2x_speed/0/stimulus.pt'), 'examine_stim_right')
    # DifferentStages(2, 'model\\model_2_types', 'testset_2x_speed', '0')
    # plotStimulus(torch.load('Q:/Documents/TDS SuperUROP/testset_2x_speed/2/stimulus.pt'), 'examine_stim_left')
    # DifferentStages(2, 'model\\model_2_types', 'testset_2x_speed', '2')
    
    # accuracy = TestFlaws(2, 'model\\model_2_types', 'testset_2x_speed', 100, printTF=True)
    # SlowVelocityTest(2, 'model\\model_2_types')
    # ResponsesAcrossDifferentStages(2, 'model\\model_2_types')
    
    # MakeVaryingDists()
    # results = FindRelevantTypes(8, 'model\\model', 'testset_lower_dist', 1.10)
    # results = FindRelevantTypes(8, 'model\\model', 'testset_lower_dist', 1.00)
    # results = FindRelevantTypes(8, 'model\\model', 'testset_lower_dist', 0.95)
    # results = FindRelevantTypes(8, 'model\\model', 'testset_upper_dist', 1.10)
    # results = FindRelevantTypes(8, 'model\\model', 'testset_upper_dist', 1.00)
    # results = FindRelevantTypes(8, 'model\\model', 'testset_upper_dist', 0.95)
    
    # accuracy = TestFlaws(2, 'model\\model_2_types', 'testset_upper_dist', 100, printTF=True)
    # accuracy = TestFlaws(8, 'model\\model', 'testset_bottom_dist', 100, printTF=True)
    # accuracy = TestFlaws(2, 'model\\model_2_types', 'testset_bottom_dist', 100, printTF=True)
    
    # best_set, high_score = PrinciplePrune(8, 'model\\model', 'testset_bottom_dist')
    # print('++++++++++++++++++++')
    # best_set, high_score = PrinciplePrune(8, 'model\\model', 'testset_top_dist')
    
    # TransplantModel_TopDist()
    # results = FindRelevantTypes(2, 'model\\model_top_dist', 'testset_top_dist', 1.00)
    # results = FindRelevantTypes(2, 'model\\model_top_dist', 'testset_upper_dist', 1.00)
    # results = FindRelevantTypes(2, 'model\\model_top_dist', 'testset_lower_dist', 1.00)
    # results = FindRelevantTypes(2, 'model\\model_top_dist', 'testset_bottom_dist', 1.00)
    # accuracy = TestFlaws(2, 'model\\model_top_dist', 'testset_top_dist', 100, printTF=True)
    # plotStimulus(torch.load('Q:/Documents/TDS SuperUROP/testset_top_dist/36/stimulus.pt'), 'examine_stim_right')
    # DifferentStages(2, 'model\\model_top_dist', 'testset_top_dist', '36')
    
    # TransplantModel_TopDist_SanAma()
    # accuracy = TestFlaws(2, 'model\\model_top_dist_san_ama', 'testset_top_dist', 50, printTF=True)
    # results = FindRelevantTypes(2, 'model\\model_top_dist_san_ama', 'testset_top_dist', 1.00)
    # DifferentStages(2, 'model\\model_top_dist_san_ama', 'testset_top_dist', '36')
    
    # dream = DreamMap().to(device)
    # TrainDeepDream(2,'model\\model_top_dist',dream,1,5000)
    # plotStimulus(dream(),'deep_dream')
    # DifferentStages(2,'model\\model_top_dist',None,None,stim=dream())
    # torch.save(dream(), 'Q:\Documents\TDS SuperUROP\\model\\right_cell_stim.pt')
    
    # TruncateModelBarLesion(2, 'model\\model_top_dist', 'testset_top_dist')
    # ExamineAmacrineResponsesinTruncated(2, 'Amacrine', 'testset_top_dist')
    # ExamineAmacrineResponsesinTruncated(2, 'Bipolar', 'testset_top_dist')
    
    # TestsetVelocityDist()
    BipolarAmacrineSubstitute()
    
    print('Fin.')