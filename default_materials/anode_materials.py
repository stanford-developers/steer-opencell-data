# %%
from steer_opencell_data.script_utils import build_plot_exporter

_plot_exporter = build_plot_exporter(__file__)
# %%
from steer_opencell_data.DataManager import DataManager
from steer_opencell_design import AnodeMaterial

from steer_materials import __version__

import plotly.express as px
import pandas as pd
# %%
import os
os.environ["OPENCELL_ENV"] = "development"
# %%
db = DataManager()
# %%
db.get_table_names()
# %%
db.drop_table('anode_materials')
# %%
db.create_table(table_name='anode_materials', columns={
    'name': 'TEXT',
    'object': 'TEXT',
    'date': 'TEXT',
    'version': 'TEXT',
    'reference': 'TEXT'
})
# %%
# Si

# Parameters
max_specific_capacity = 3580  # mAh/g
round_trip_efficiency = 0.95  # 95% efficiency

# Create charge curve (0 to max capacity)
charge_curve = (
    pd.read_csv(
        '../local_data/active_materials/anode/Si removed-vendor (420 mAh g).csv',
        names=['volts', 'soc'],
        skiprows=1
    ).assign(
        specific_capacity=lambda df: df.soc * max_specific_capacity,
        voltage=lambda df: df.volts,
        direction='charge'
    )
)

# Create discharge curve (max capacity to max * efficiency)
discharge_end_capacity = max_specific_capacity * round_trip_efficiency

discharge_curve = (
    charge_curve
    .copy()
    .assign(specific_capacity = lambda x: -x["specific_capacity"] + x["specific_capacity"].max())
    .sort_values('specific_capacity', ascending=True)
    .assign(
        specific_capacity=lambda df: df.specific_capacity * round_trip_efficiency,
        direction='discharge'
    )
    .reset_index(drop=True)
)

# Combine charge and discharge curves (downsample to every 5th point)
half_cell = pd.concat([
    charge_curve[['specific_capacity', 'voltage', 'direction']].iloc[::20],
    discharge_curve[['specific_capacity', 'voltage', 'direction']].iloc[::20]
], ignore_index=True)

# Create AnodeMaterial
si = AnodeMaterial(
    name = 'Si (Vendor A)',
    reference = 'Li/Li+',
    specific_cost = 15.00,
    density = 2.33,
    specific_capacity_curves = half_cell,
    color='#8B4513'
)

_plot_exporter.save(
    si.plot_underlying_specific_capacity_curves(width=900, height=500),
    'plot_underlying_specific_capacity_curves',
)
# %%
# SiGr

# Parameters
max_specific_capacity = 440  # mAh/g
round_trip_efficiency = 0.95  # 95% efficiency

# Create charge curve (0 to max capacity)
charge_curve = (
    pd.read_csv(
        '../local_data/active_materials/anode/SiGr removed-vendor50E (440 mAh g).csv',
        names=['volts', 'soc'],
        skiprows=1
    ).assign(
        specific_capacity=lambda df: df.soc * max_specific_capacity,
        voltage=lambda df: df.volts,
        direction='charge'
    )
    .sort_values('specific_capacity', ascending=True)
)

# Create discharge curve (max capacity to max * efficiency)
discharge_end_capacity = max_specific_capacity * round_trip_efficiency

discharge_curve = (
    charge_curve
    .copy()
    .assign(specific_capacity = lambda x: -x["specific_capacity"] + x["specific_capacity"].max())
    .sort_values('specific_capacity', ascending=True)
    .assign(
        specific_capacity=lambda df: df.specific_capacity * round_trip_efficiency,
        direction='discharge'
    )
    .reset_index(drop=True)
)

# Combine charge and discharge curves
half_cell = pd.concat([
    charge_curve[['specific_capacity', 'voltage', 'direction']],
    discharge_curve[['specific_capacity', 'voltage', 'direction']]
], ignore_index=True)

# Create AnodeMaterial
sigr = AnodeMaterial(
    name = 'SiGr (Vendor A)',
    reference = 'Li/Li+',
    specific_cost = 15.00,
    density = 2.33,
    specific_capacity_curves = half_cell,
    color='#8B4513'
)

_plot_exporter.save(
    sigr.plot_underlying_specific_capacity_curves(width=900, height=500),
    'plot_underlying_specific_capacity_curves',
)
# %%
# hc1

half_cell = (
    pd.read_csv(
        '../local_data/active_materials/anode/Hard Carbon (Vendor A - 330 mAh g).csv',
        names=['specific_capacity', 'voltage', 'direction', 'id'],
        skiprows=1
    ).drop(
        columns=['id']
    ).assign(
        direction = lambda x: x['direction'].apply(lambda y: 'discharge' if y == 'CC_DChg' else 'charge'),
    )
)

hc1 = AnodeMaterial(
    name = 'Hard Carbon (Vendor A)',
    reference = 'Na/Na+',
    specific_cost = 4.5,
    density = 1.5,
    specific_capacity_curves = half_cell,
    color='#1a1a1a'
)

_plot_exporter.save(
    hc1.plot_underlying_specific_capacity_curves(width=900, height=500),
    'plot_underlying_specific_capacity_curves',
)

_plot_exporter.save(
    px.line(half_cell, x='specific_capacity', y='voltage', color='direction'),
    'line',
)
# %%
# hc2

half_cell = (
    pd.read_csv(
        '../local_data/active_materials/anode/Hard Carbon (Vendor B - 300 mAh g).csv',
        names=['specific_capacity', 'voltage', 'direction', 'id'],
        skiprows=1
    ).drop(
        columns=['id']
    ).assign(
        direction = lambda x: x['direction'].apply(lambda y: 'discharge' if y == 'CC_DChg' else 'charge'),
    )
)

# px.line(half_cell, x='specific_capacity', y='voltage', markers=True, color='direction').show()

hc2 = AnodeMaterial(
    name = 'Hard Carbon (Vendor B)',
    reference = 'Na/Na+',
    specific_cost = 4.5,
    density = 1.5,
    specific_capacity_curves = half_cell,
    color='#1a1a1a'
)

_plot_exporter.save(
    hc2.plot_underlying_specific_capacity_curves(width=900, height=500),
    'plot_underlying_specific_capacity_curves',
)
# %%
# hc4

half_cell = (
    pd.read_csv(
        '../local_data/active_materials/anode/Hard Carbon (Vendor D1 - 300 mAh g).csv',
        names=['specific_capacity', 'voltage', 'direction', 'id'],
        skiprows=1
    ).drop(
        columns=['id']
    ).assign(
        direction = lambda x: x['direction'].apply(lambda y: 'discharge' if y == 'CC_DChg' else 'charge'),
    )
)

# px.line(half_cell, x='specific_capacity', y='voltage', markers=True, color='direction').show()

hc4 = AnodeMaterial(
    name = 'Hard Carbon (Vendor D)',
    reference = 'Na/Na+',
    specific_cost = 4.5,
    density = 1.5,
    specific_capacity_curves = half_cell,
    color='#1a1a1a'
)

_plot_exporter.save(
    hc4.plot_underlying_specific_capacity_curves(width=900, height=500),
    'plot_underlying_specific_capacity_curves',
)
# %%
# hc5

half_cell = (
    pd.read_csv(
        '../local_data/active_materials/anode/Hard Carbon (Vendor D2 - 300 mAh g).csv',
        names=['specific_capacity', 'voltage', 'direction', 'id'],
        skiprows=1
    ).drop(
        columns=['id']
    ).assign(
        direction = lambda x: x['direction'].apply(lambda y: 'discharge' if y == 'CC_DChg' else 'charge'),
    )
)

# px.line(half_cell, x='specific_capacity', y='voltage', markers=True, color='direction').show()

hc5 = AnodeMaterial(
    name = 'Hard Carbon (Vendor E)',
    reference = 'Na/Na+',
    specific_cost = 4.5,
    density = 1.5,
    specific_capacity_curves = half_cell,
    color='#1a1a1a'
)

_plot_exporter.save(
    hc5.plot_underlying_specific_capacity_curves(width=900, height=500),
    'plot_underlying_specific_capacity_curves',
)
# %%
# lead

half_cell = (
    pd.read_csv(
        '../local_data/active_materials/anode/lead.csv',
        names=['specific_capacity', 'voltage', 'direction', 'id'],
        skiprows=1
    ).drop(
        columns=['id']
    ).assign(
        direction = lambda x: x['direction'].apply(lambda y: 'discharge' if y == 'CC_DChg' else 'charge'),
    )
)

# px.line(half_cell, x='specific_capacity', y='voltage', markers=True, color='direction').show()

pb = AnodeMaterial(
    name = 'Lead',
    reference = 'Na/Na+',
    specific_cost = 2.50,
    density = 11.340,
    specific_capacity_curves = half_cell,
    color='#6e7f80'
)

_plot_exporter.save(
    pb.plot_underlying_specific_capacity_curves(width=900, height=500),
    'plot_underlying_specific_capacity_curves',
)
# %%
# Synthetic Graphite

half_cell = (
    pd.read_csv(
        '../local_data/active_materials/anode/Synthetic Graphite.csv',
        names=['specific_capacity', 'voltage', 'direction', 'id'],
        skiprows=1
    ).drop(
        columns=['id']
    ).assign(
        direction = lambda x: x['direction'].apply(lambda y: 'discharge' if y == 'CC_DChg' else 'charge'),
    )
)

# px.line(half_cell, x='specific_capacity', y='voltage', markers=True, color='direction').show()

sg = AnodeMaterial(
    name = 'Synthetic Graphite',
    reference = 'Li/Li+',
    specific_cost = 6.70,
    density = 2.25,
    specific_capacity_curves = half_cell,
    color='#6e7f80'
)

_plot_exporter.save(
    sg.plot_underlying_specific_capacity_curves(width=900, height=500),
    'plot_underlying_specific_capacity_curves',
)
# %%
# Tin

half_cell = (
    pd.read_csv(
        '../local_data/active_materials/anode/Tin.csv',
        names=['specific_capacity', 'voltage', 'direction', 'id'],
        skiprows=1
    ).drop(
        columns=['id']
    ).assign(
        direction = lambda x: x['direction'].apply(lambda y: 'discharge' if y == 'CC_DChg' else 'charge'),
    )
)

# px.line(half_cell, x='specific_capacity', y='voltage', markers=True, color='direction').show()

tn = AnodeMaterial(
    name = 'Tin',
    reference = 'Na/Na+',
    specific_cost = 2.50,
    density = 7.31,
    specific_capacity_curves = half_cell,
    color='#6e7f80'
)

_plot_exporter.save(
    tn.plot_underlying_specific_capacity_curves(width=900, height=500),
    'plot_underlying_specific_capacity_curves',
)
# %%
materials = [
    hc1, hc2, hc4, hc5, pb, sg, tn, si, sigr
]

pickled_materials = [m.serialize() for m in materials]
# %%

db.insert_data(table_name='anode_materials', data=pd.DataFrame({
    'name': [m.name for m in materials],
    'object': pickled_materials,
    'date': [m.last_updated for m in materials],
    'version': [__version__ for m in materials],
    'reference': [m.reference for m in materials]
}))
# %%
db.get_anode_materials(most_recent=True)
