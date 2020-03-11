import pandas as pd
import calendar
import os


class Monthly2Yearly:

    def __init__(self,inputpath, outputpath, DoNotReadFiles=[]):

        # Put all foldername in order in a list
        FolderNameList = ['Category_'+calendar.month_name[i+1][0:3] for i in range(12)]
        PVScenarios_list = ['{}.0%-customer-100.0%-PV'.format((i+1)*10) for i in range(10)]
        PVScenarios_list = PVScenarios_list+['Base']
        MetricAddition = ['{}Asset.csv'.format(metric) for metric in ['CRI','LVRI','TVRI','NVRI','TLOF','TOG']]
        MetricAverage= ['{}Asset.csv'.format(metric) for metric in ['LE','TE']]


        # Walk through all folders inside input path

        for PVScenario in PVScenarios_list:
            AllDataDict = {}
            print('Converting monthly result to annual for {} scenario ..............................................'.format(PVScenario))
            if not os.path.exists(os.path.join(outputpath,PVScenario)): os.mkdir(os.path.join(outputpath,PVScenario))

            for Folder in FolderNameList:
                assert os.path.exists(os.path.join(inputpath,Folder,PVScenario)),'{} does not exists.'.format(os.path.join(inputpath,Folder,PVScenario))
                for files in os.listdir(os.path.join(inputpath,Folder,PVScenario)):
                    if 'TimeSeries.csv' in files and files not in DonotReadFilesList:
                        if files not in AllDataDict: AllDataDict[files] = []
                        AllDataDict[files].append(pd.read_csv(os.path.join(inputpath,Folder,PVScenario,files)))

                    elif files not in DonotReadFilesList:

                        if files not in AllDataDict:
                            AllDataDict[files] = pd.read_csv(os.path.join(inputpath,Folder,PVScenario,files))
                        else:
                            this_dataframe = pd.read_csv(os.path.join(inputpath,Folder,PVScenario,files))
                            AllDataDict[files]['Values']  =[sum(x) for x in zip(AllDataDict[files]['Values'].tolist(),this_dataframe['Values'].tolist())]


            for keys, values in AllDataDict.items():
                if 'TimeSeries.csv' in keys:
                    df = pd.concat(values)
                    df.to_csv(os.path.join(outputpath,PVScenario,keys),index=False)
                    print('{} created successfully'.format(os.path.join(outputpath,PVScenario,keys)))

                elif keys in MetricAverage:
                    values['Values'] = [el/12 for el in values['Values']]
                    values.to_csv(os.path.join(outputpath, PVScenario, keys), index=False)
                    print('{} created successfully'.format(os.path.join(outputpath, PVScenario, keys)))

                elif keys == 'SystemLevelMetrics.csv':
                    datadict = dict(zip(values['Metrics'],values['Values']))
                    keys_to_average = ['SE_line','SE_transformer','SE']
                    for key,val in datadict.items():
                        if key in keys_to_average: datadict[key] = val/12
                    datadictmodified = {'Metrics':[k for k in datadict.keys()],'Values': [v for k,v in datadict.items()]}
                    df = pd.DataFrame.from_dict(datadictmodified)
                    df.to_csv(os.path.join(outputpath, PVScenario, keys), index=False)
                    print('{} created successfully'.format(os.path.join(outputpath, PVScenario, keys)))
                else:
                    values.to_csv(os.path.join(outputpath,PVScenario,keys),index=False)
                    print('{} created successfully'.format(os.path.join(outputpath, PVScenario, keys)))


if __name__ =='__main__':

    inputpath = r"C:\Users\KDUWADI\Desktop\NREL_Projects\CIFF-TANGEDCO\TANGEDCO\SoftwareTools\CombineMonthlyResults\MonthlyResults\GWC"
    outputpath = r"C:\Users\KDUWADI\Desktop\NREL_Projects\CIFF-TANGEDCO\TANGEDCO\SoftwareTools\CombineMonthlyResults\YearlyResults\GWC"
    DonotReadFilesList = ['voltagemagAssetTimeSeries.csv','lineloadingAssetTimeSeries.csv','transformerloadingAssetTimeSeries.csv']
    Monthly2Yearly(inputpath,outputpath,DonotReadFilesList)




