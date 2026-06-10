# %%
from steer_opencell_data.script_utils import build_plot_exporter

_plot_exporter = build_plot_exporter(__file__)
# %%
from steer_opencell_data.DataManager import DataManager
from steer_opencell_design import CathodeMaterial
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
db.drop_table('cathode_materials')
# %%
db.create_table(table_name='cathode_materials', columns={
    'name': 'TEXT',
    'object': 'TEXT',
    'date': 'TEXT',
    'version': 'TEXT',
    'reference': 'TEXT'
})
# %%
# LFP

half_cell = (
    pd.read_csv(
        '../local_data/active_materials/cathode/LFP.csv',
        names=['specific_capacity', 'voltage', 'direction', 'id'],
        skiprows=1
    ).drop(
        columns=['id']
    ).assign(
        direction = lambda x: x['direction'].apply(lambda y: 'discharge' if y == 'CC_DChg' else 'charge'),
    )
)

lfp = CathodeMaterial(
    name = 'LFP',
    reference = 'Li/Li+',
    specific_cost = 6.70,
    density = 3.6,
    specific_capacity_curves = half_cell,
    color='#2c2c2c',
    extrapolation_window=0.5
)

_plot_exporter.save(
    lfp.plot_underlying_specific_capacity_curves(width=900, height=500),
    'plot_underlying_specific_capacity_curves',
)
# %%
# NNM

csv1 = '../local_data/active_materials/cathode/NaNiMn P2-O3 Composite - 4.1V.csv'
csv2 = '../local_data/active_materials/cathode/NaNiMn P2-O3 Composite - 4.25V.csv'
csv3 = '../local_data/active_materials/cathode/NaNiMn P2-O3 Composite - 4.35V.csv'

half_cells = []
for csv in [csv1, csv2, csv3]:

    half_cell = (
        pd.read_csv(
            csv,
            names=['specific_capacity', 'voltage', 'direction', 'id'],
            skiprows=1
        ).drop(
            columns=['id']
        ).assign(
            direction = lambda x: x['direction'].apply(lambda y: 'discharge' if y == 'CC_DChg' else 'charge'),
        )
    )

    half_cells.append(half_cell)

nnm = CathodeMaterial(
    name = 'NaNiMn P2-O3 Composite',
    reference = 'Na/Na+',
    specific_cost = 11.00,
    density = 4.4,
    specific_capacity_curves = half_cells,
    color='#1f1f1f'
)

_plot_exporter.save(
    nnm.plot_underlying_specific_capacity_curves(width=900, height=500),
    'plot_underlying_specific_capacity_curves',
)
# %%
# NFM vendor 1

half_cell = (
    pd.read_csv(
        '../local_data/active_materials/cathode/NFM111 (Vendor A).csv',
        names=['specific_capacity', 'voltage', 'direction', 'id'],
        skiprows=1
    ).drop(
        columns=['id']
    ).assign(
        direction = lambda x: x['direction'].apply(lambda y: 'discharge' if y == 'CC_DChg' else 'charge'),
    )
)

nfm1 = CathodeMaterial(
    name = 'NFM111 (Vendor A)',
    reference = 'Na/Na+',
    specific_cost = 8.00,
    density = 4.25,
    specific_capacity_curves = half_cell,
    color='#2b1f1a'
)

_plot_exporter.save(
    nfm1.plot_underlying_specific_capacity_curves(width=900, height=500),
    'plot_underlying_specific_capacity_curves',
)
# %%
# NFM vendor 2

half_cell = (
    pd.read_csv(
        '../local_data/active_materials/cathode/NFM111 (Vendor B).csv',
        names=['specific_capacity', 'voltage', 'direction', 'id'],
        skiprows=1
    ).drop(
        columns=['id']
    ).assign(
        direction = lambda x: x['direction'].apply(lambda y: 'discharge' if y == 'CC_DChg' else 'charge'),
    )
)

nfm2 = CathodeMaterial(
    name = 'NFM111 (Vendor B)',
    reference = 'Na/Na+',
    specific_cost = 8.00,
    density = 4.25,
    specific_capacity_curves = half_cell,
    color='#2b1f1a'
)

_plot_exporter.save(
    nfm2.plot_underlying_specific_capacity_curves(width=900, height=500),
    'plot_underlying_specific_capacity_curves',
)
# %%
# NFM Vendor 3

half_cell = (
    pd.read_csv(
        '../local_data/active_materials/cathode/NFM111 (Vendor C).csv',
        names=['time', 'voltage', 'capacity', 'id', 'discharge_charge', 'charge_charge'],
        # names=['specific_capacity', 'voltage', 'direction', 'id'],
        skiprows=1
    ).assign(
        direction = lambda x: x['id'].apply(lambda y: 'charge' if y == 0 else 'discharge')
    ).assign(
        specific_capacity = lambda x: x['capacity'] / (3.786e-3),
        direction = lambda x: x['time'].apply(lambda y: 'charge' if y < 25545.76 else 'discharge'),
    ).drop(
        columns=['id', 'charge_charge', 'discharge_charge', 'capacity']
    )
)

nfm3 = CathodeMaterial(
    name = 'NFM111 (Vendor C)',
    reference = 'Na/Na+',
    specific_cost = 8.00,
    density = 4.25,
    specific_capacity_curves = half_cell,
    color='#2b1f1a'
)

_plot_exporter.save(
    nfm3.plot_underlying_specific_capacity_curves(width=900, height=500),
    'plot_underlying_specific_capacity_curves',
)
# %%
# NFPP

half_cell = (
    pd.read_csv(
        '../local_data/active_materials/cathode/NFPP.csv',
        names=['specific_capacity', 'voltage', 'direction', 'id'],
        skiprows=1
    ).drop(
        columns=['id']
    ).assign(
        direction = lambda x: x['direction'].apply(lambda y: 'discharge' if y == 'CC_DChg' else 'charge'),
    )
)

nfpp = CathodeMaterial(
    name = 'NFPP',
    reference = 'Na/Na+',
    specific_cost = 4.50,
    density = 2.95,
    specific_capacity_curves = half_cell,
    color='#7b3f00'
)

_plot_exporter.save(
    nfpp.plot_underlying_specific_capacity_curves(width=900, height=500),
    'plot_underlying_specific_capacity_curves',
)
# %%
# NMC622

half_cell = (
    pd.read_csv(
        '../local_data/active_materials/cathode/NMC622.csv',
        names=['specific_capacity', 'voltage', 'direction', 'id'],
        skiprows=1
    ).drop(
        columns=['id']
    ).assign(
        direction = lambda x: x['direction'].apply(lambda y: 'discharge' if y == 'CC_DChg' else 'charge'),
    )
)

nmc622 = CathodeMaterial(
    name = 'NMC622',
    reference = 'Li/Li+',
    specific_cost = 17.6,
    density = 4.75,
    specific_capacity_curves = half_cell,
    color='#9daaa2'
)

_plot_exporter.save(
    nmc622.plot_underlying_specific_capacity_curves(width=900, height=500),
    'plot_underlying_specific_capacity_curves',
)
# %%
# NMC811

half_cell = (
    pd.read_csv(
        '../local_data/active_materials/cathode/NMC811.csv',
        names=['specific_capacity', 'voltage', 'direction', 'id'],
        skiprows=1
    ).drop(
        columns=['id']
    ).assign(
        direction = lambda x: x['direction'].apply(lambda y: 'discharge' if y == 'CC_DChg' else 'charge'),
    )
)

nmc811 = CathodeMaterial(
    name = 'NMC811',
    reference = 'Li/Li+',
    specific_cost = 20.70,
    density = 4.8,
    specific_capacity_curves = half_cell,
    color='#7f8f87'
)

_plot_exporter.save(
    nmc811.plot_underlying_specific_capacity_curves(width=900, height=500),
    'plot_underlying_specific_capacity_curves',
)
# %%
# NVP

half_cell = (
    pd.read_csv(
        '../local_data/active_materials/cathode/NVP.csv',
        names=['specific_capacity', 'voltage', 'direction', 'id'],
        skiprows=1
    ).drop(
        columns=['id']
    ).assign(
        direction = lambda x: x['direction'].apply(lambda y: 'discharge' if y == 'CC_DChg' else 'charge'),
    )
)

nvp = CathodeMaterial(
    name = 'NVP',
    reference = 'Na/Na+',
    specific_cost = 20.00,
    density = 3.2,
    specific_capacity_curves = half_cell,
    color='#c2b280',
    extrapolation_window=0.3
)

_plot_exporter.save(
    nvp.plot_underlying_specific_capacity_curves(
        width=900,
        height=500
    ),
    'plot_underlying_specific_capacity_curves',
)
# %%
# NVPF

half_cell = (
    pd.read_csv(
        '../local_data/active_materials/cathode/NVPF.csv',
        names=['specific_capacity', 'voltage', 'direction', 'id'],
        skiprows=1
    ).drop(
        columns=['id']
    ).assign(
        direction = lambda x: x['direction'].apply(lambda y: 'discharge' if y == 'CC_DChg' else 'charge'),
    )
)

nvpf = CathodeMaterial(
    name = 'NVPF',
    reference = 'Na/Na+',
    specific_cost = 20.00,
    density = 3.3,
    specific_capacity_curves = half_cell,
    color="#7f7f7f"
)

_plot_exporter.save(
    nvpf.plot_underlying_specific_capacity_curves(width=900, height=500),
    'plot_underlying_specific_capacity_curves',
)
# %%
# Prussian White

half_cell = (
    pd.read_csv(
        '../local_data/active_materials/cathode/Prussian White.csv',
        names=['specific_capacity', 'voltage', 'direction', 'id'],
        skiprows=1
    ).drop(
        columns=['id']
    ).assign(
        direction = lambda x: x['direction'].apply(lambda y: 'discharge' if y == 'CC_DChg' else 'charge'),
    )
)

pw = CathodeMaterial(
    name = 'Prussian White',
    reference = 'Na/Na+',
    specific_cost = 15.00,
    density = 2.0,
    specific_capacity_curves = half_cell,
    color="#83bffb"
)

_plot_exporter.save(
    pw.plot_underlying_specific_capacity_curves(width=900, height=500),
    'plot_underlying_specific_capacity_curves',
)
# %%
# %%
materials = [
    lfp,
    nnm,
    nfm1,
    nfm2,
    nfm3,
    nfpp,
    nmc622,
    nmc811,
    nvp,
    nvpf,
    pw
]

pickled_materials = [m.serialize() for m in materials]
# %%

db.insert_data(table_name='cathode_materials', data=pd.DataFrame({
    'name': [m.name for m in materials],
    'object': pickled_materials,
    'date': [m.last_updated for m in materials],
    'version': [__version__ for m in materials],
    'reference': [m.reference for m in materials]
}))
# %%
db.get_cathode_materials(most_recent=False)
# %%
db.get_cathode_materials(most_recent=True)
