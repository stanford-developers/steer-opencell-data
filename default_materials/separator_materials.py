# %%
from steer_opencell_data.DataManager import DataManager
from steer_opencell_design import SeparatorMaterial
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
db.drop_table('separator_materials')
# %%
db.create_table(table_name='separator_materials', columns={
    'name': 'TEXT',
    'object': 'TEXT',
    'date': 'TEXT',
    'version': 'TEXT'
})
# %%
# materials

polyethylene = SeparatorMaterial(
    name="Polyethylene",
    density=0.94,
    specific_cost=20.0,
    color="#f2f2f2",
    porosity=40
)

polypropylene = SeparatorMaterial(
    name="Polypropylene",
    density=0.91,
    specific_cost=15.0,
    color="#fafafa",
    porosity=40
)

glass_fiber = SeparatorMaterial(
    name="Glass Fiber",
    density=2.5,
    specific_cost=5.0,
    color="#dcdcdc",
    porosity=75
)

ceramic_coated_pe = SeparatorMaterial(
    name="Ceramic-coated PE",
    density=1.2,
    specific_cost=40.0,
    color="#e6e6e6",
    porosity=40
)

cellulose = SeparatorMaterial(
    name="Cellulose",
    density=1.5,
    specific_cost=2.0,
    color="#f5f5dc",
    porosity=60
)

peo = SeparatorMaterial(
    name="Polyethylene Oxide",
    density=1.2,
    specific_cost=50.0,
    color="#ffffff",
    porosity=20
)

pvdf_hfp = SeparatorMaterial(
    name="PVDF-HFP",
    density=1.78,
    specific_cost=60.0,
    color="#f0f8ff",
    porosity=55
)

nafion = SeparatorMaterial(
    name="Nafion",
    density=2.0,
    specific_cost=1000.0,
    color="#e0ffff",
    porosity=30
)

nonwoven_polymer = SeparatorMaterial(
    name="Nonwoven Polymer",
    density=1.0,
    specific_cost=10.0,
    color="#eeeeee",
    porosity=65
)

composite_separator = SeparatorMaterial(
    name="Polymer-Ceramic Composite",
    density=1.5,
    specific_cost=35.0,
    color="#f8f8ff",
    porosity=50
)
# %%
materials = [
    polyethylene,
    polypropylene,
    glass_fiber,
    ceramic_coated_pe,
    cellulose,
    peo,
    pvdf_hfp,
    nafion,
    nonwoven_polymer,
    composite_separator
]

pickled_materials = [m.serialize() for m in materials]
# %%
# store data for current collectors

db.insert_data(table_name='separator_materials', data=pd.DataFrame({
    'name': [m.name for m in materials],
    'object': pickled_materials,
    'date': [m.last_updated for m in materials],
    'version': [__version__ for m in materials],
}))
# %%
db.get_separator_materials(most_recent=False)
# %%
db.get_separator_materials()
# %% [markdown]
