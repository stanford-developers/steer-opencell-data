# %%
from steer_opencell_data.DataManager import DataManager
from steer_opencell_design import Binder
from steer_materials import __version__
import pandas as pd
# %%
import os
os.environ["OPENCELL_ENV"] = "development"
# %%
db = DataManager()
# %%
db.get_table_names()
# %%
db.drop_table('binder_materials')
# %%
db.create_table(table_name='binder_materials', columns={
    'name': 'TEXT',
    'object': 'TEXT',
    'date': 'TEXT',
    'version': 'TEXT'
})
# %%
# materials

pvdf = Binder(name='PVDF', density=1.78, specific_cost=16.6, color='#e5e5e5')
sbr = Binder(name='SBR', density=0.94, specific_cost=1, color='#f4e3d7')
cmc = Binder(name='CMC', density=1.6, specific_cost=3, color='#d6cfc7')
paa = Binder(name='PAA', density=1.22, specific_cost=3, color='#e4dada')
alg = Binder(name='Alginate', density=1.6, specific_cost=2, color='#c2b280')

materials = [pvdf, sbr, cmc, paa, alg]

pickled_materials = [m.serialize() for m in materials]
# %%
# store data for current collectors

db.insert_data(table_name='binder_materials', data=pd.DataFrame({
    'name': [m.name for m in materials],
    'object': pickled_materials,
    'date': [m.last_updated for m in materials],
    'version': [__version__ for m in materials],
}))
# %%
db.get_binder_materials(most_recent=False)
# %%
db.get_binder_materials()
# %%
binder = Binder.from_database('PVDF')
# %% [markdown]
