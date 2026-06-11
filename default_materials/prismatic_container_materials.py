# %%
from steer_opencell_data.DataManager import DataManager
from steer_opencell_design import PrismaticContainerMaterial
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
db.drop_table('prismatic_container_materials')
# %%
db.create_table(table_name='prismatic_container_materials', columns={
    'name': 'TEXT',
    'object': 'TEXT',
    'date': 'TEXT',
    'version': 'TEXT'
})
# %%
# materials

aluminum = PrismaticContainerMaterial(
    name='Aluminum',
    density=2.70,
    specific_cost=2.9,
    color='#C0C0C0'
)

steel = PrismaticContainerMaterial(
    name='Steel',
    density=7.85,
    specific_cost=0.5,
    color='#808080'
)

copper = PrismaticContainerMaterial(
    name='Copper',
    density=8.96,
    specific_cost=15.5,
    color='#B87333'
)


materials = [aluminum, steel, copper]
pickled_materials = [m.serialize() for m in materials]
# %%
# store data for current collectors

db.insert_data(table_name='prismatic_container_materials', data=pd.DataFrame({
    'name': [m.name for m in materials],
    'object': pickled_materials,
    'date': [m.last_updated for m in materials],
    'version': [__version__ for m in materials],
}))
# %%
db.get_prismatic_container_materials(most_recent=False)
# %%
db.get_prismatic_container_materials()
# %% [markdown]
