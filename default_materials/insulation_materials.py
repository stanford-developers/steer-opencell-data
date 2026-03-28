# %%
from steer_opencell_data.DataManager import DataManager
from steer_opencell_design import InsulationMaterial
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
db.drop_table('insulation_materials')
# %%
db.create_table(table_name='insulation_materials', columns={
    'name': 'TEXT',
    'object': 'TEXT',
    'date': 'TEXT',
    'version': 'TEXT'
})
# %%
# materials

aluminium_oxide_95 = InsulationMaterial(
    name='Aluminium Oxide, 95%',
    density=3.65,
    specific_cost=20,
    color='#B0A99F'
)

aluminium_oxide_96 = InsulationMaterial(
    name='Aluminium Oxide, 96%',
    density=3.72,
    specific_cost=55,
    color='#D4CDC5'
)

aluminium_oxide_99 = InsulationMaterial(
    name='Aluminium Oxide, 99.5%',
    density=3.87,
    specific_cost=115,
    color='#EAEAEA'
)

aluminium_oxide_999 = InsulationMaterial(
    name='Aluminium Oxide, 99.9%',
    density=3.92,
    specific_cost=225,
    color='#F7F7F7'
)

sapphire = InsulationMaterial(
    name='Sapphire',
    density=3.99,
    specific_cost=1000,
    color='#A9C8E3'
)
# %%
materials = [
    aluminium_oxide_95,
    aluminium_oxide_96,
    aluminium_oxide_99,
    aluminium_oxide_999,
    sapphire
]

pickled_materials = [m.serialize() for m in materials]
# %%
# store data for current collectors

db.insert_data(table_name='insulation_materials', data=pd.DataFrame({
    'name': [m.name for m in materials],
    'object': pickled_materials,
    'date': [m.last_updated for m in materials],
    'version': [__version__ for m in materials],
}))
# %%
db.get_insulation_materials(most_recent=False)
# %%
db.get_insulation_materials()
# %% [markdown]
