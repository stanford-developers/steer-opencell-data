# %%
from steer_opencell_data.DataManager import DataManager
from steer_opencell_design import ConductiveAdditive
from steer_opencell_design import __version__
import pandas as pd
# %%
import os
os.environ["OPENCELL_ENV"] = "development"
# %%
db = DataManager()
# %%
db.get_table_names()
# %%
db.drop_table('conductive_additive_materials')
# %%
db.create_table(table_name='conductive_additive_materials', columns={
    'name': 'TEXT',
    'object': 'TEXT',
    'date': 'TEXT',
    'version': 'TEXT'
})
# %%
# materials

superp = ConductiveAdditive(name='Super P', density=2.0, specific_cost=15.0, color='#111111')
ketjenblack = ConductiveAdditive(name='Ketjenblack EC-600JD', density=1.8, specific_cost=30.0, color='#0f0f0f')
acetylene_black = ConductiveAdditive(name='Acetylene Black', density=1.8, specific_cost=15.0, color='#1a1a1a')
graphite = ConductiveAdditive(name='Graphite', density=2.2, specific_cost=10.0, color='#4d4d4d')
carbon_nanotubes = ConductiveAdditive(name='Carbon Nanotubes', density=1.75, specific_cost=250.0, color='#1b1b1b')
graphene = ConductiveAdditive(name='Graphene', density=2.2, specific_cost=350.0, color='#2c2c2c')
vgcf = ConductiveAdditive(name='Vapor Grown Carbon Fibers', density=2.0, specific_cost=75, color='#262626')

materials = [superp, ketjenblack, acetylene_black, graphite, carbon_nanotubes, graphene, vgcf]

pickled_materials = [m.serialize() for m in materials]
# %%
# store data for current collectors

db.insert_data(table_name='conductive_additive_materials', data=pd.DataFrame({
    'name': [m.name for m in materials],
    'object': pickled_materials,
    'date': [m.last_updated for m in materials],
    'version': [__version__ for m in materials],
}))
# %%
db.get_conductive_additive_materials(most_recent=False)
# %%
db.get_conductive_additive_materials()
# %% [markdown]
