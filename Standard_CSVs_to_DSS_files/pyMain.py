
import os,pathlib
import toml
from pyReader import Reader
from pyWriter import Writer
import shutil

def create_scenario_dict(settings_dict):
    scenario_dict = {}
    scenario_dict['Base'] = {'PPV_customers': 0, 'PPV_capacity': 0}
    for i in range(settings_dict['PV_capacity_step']):
        for j  in range(settings_dict['PV_customers_step']):
            customer = 100*(j+1)/(settings_dict['PV_customers_step'])
            capacity = 100*(i+1)/(settings_dict['PV_capacity_step'])
            scenario_dict[str(customer) + '%-customer-'+str(capacity)+'%-PV'] = {'PPV_customers': customer , 'PPV_capacity':capacity }

    return scenario_dict

def readtoml(setting_toml_file):

    texts = ''
    f = open(setting_toml_file, "r")
    text = texts.join(f.readlines())
    settings_dict = toml.loads(text,_dict=dict)
    return settings_dict

def ClearProjectFolder(path):
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    for root, dirs, files in os.walk(path):
        for f in files:
            os.unlink(os.path.join(root, f))
        for d in dirs:
            shutil.rmtree(os.path.join(root, d))
    return

if __name__ == '__main__':
    setting_toml_file = r'C:\Users\KDUWADI\Desktop\NREL_Projects\CIFF-TANGEDCO\TANGEDCO\SoftwareTools\Standard_CSVs_to_DSS_files\scenario.toml'
    settings_dict = readtoml(setting_toml_file)
    scenario_dict = create_scenario_dict(settings_dict)
    network = Reader(settings_dict)
    path_to_export = os.path.join(settings_dict['Project path'],'ExportedDSSfiles')
    ClearProjectFolder(path_to_export)
    for keys, values in scenario_dict.items():
        print('-------------------------'+keys + ' Scenario' + '----------------------------------------')
        if values['PPV_capacity'] in [0,100] and values['PPV_customers'] in [0,100] or settings_dict['number_of_monte_carlo_run'] == 1:
            Writer(network, settings_dict,os.path.join(path_to_export,keys), values['PPV_customers']/100,values['PPV_capacity']/100)
        else:
            if settings_dict['number_of_monte_carlo_run'] >= 1:
                if not os.path.exists(os.path.join(path_to_export,keys)): os.mkdir(os.path.join(path_to_export,keys))
                for j in range(settings_dict['number_of_monte_carlo_run']):
                    Writer(network, settings_dict,os.path.join(path_to_export,keys,'monte_carlo_'+str(j)), values['PPV_customers']/100,values['PPV_capacity']/100)

