# %%
from steer_opencell_data.script_utils import build_plot_exporter

_plot_exporter = build_plot_exporter(__file__)
# %%
from steer_opencell_data.DataManager import DataManager
import steer_opencell_design as ocd
# %%
# User Inputs

####################

table_name = 'cell_references' #### change this to cell_teardowns for teardowns
cell_name = "NMC811 Stacked Pouch Cell"

#####################
# %%
import os
os.environ["OPENCELL_ENV"] = "development"
# %%
# set some standard materials

conductive_additive = ocd.ConductiveAdditive.from_database("Super P")
binder = ocd.Binder.from_database("PVDF")
insulation = ocd.InsulationMaterial.from_database("Aluminium Oxide, 95%")
separator_material = ocd.SeparatorMaterial.from_database('Polyethylene')
tape_material = ocd.TapeMaterial.from_database("Kapton")
prismatic_material = ocd.PrismaticContainerMaterial.from_database("Steel")
# %%
# Create the cathode

cathode_current_collector_material = ocd.CurrentCollectorMaterial.from_database('Aluminum')

cathode_current_collector=ocd.PunchedCurrentCollector(
    material=cathode_current_collector_material,
    width=300,
    height=280,
    tab_height=30,
    tab_position=70,
    tab_width=80,
    thickness=10,
    insulation_width=2
)

cathode_active_material = ocd.CathodeMaterial.from_database("NMC811")

cathode_formulation = ocd.CathodeFormulation(
    active_materials={cathode_active_material: 95},
    binders={binder: 2.5},
    conductive_additives={conductive_additive: 2.5}
)

my_cathode = ocd.Cathode(
    formulation=cathode_formulation,
    current_collector=cathode_current_collector,
    calender_density=3.4,
    mass_loading=14,
    insulation_material=insulation,
    insulation_thickness=3
)
# %%
# Create the anode

cathode_current_collector_material = ocd.CurrentCollectorMaterial.from_database("Copper")

anode_current_collector = ocd.PunchedCurrentCollector(
    material=cathode_current_collector_material,
    width=300,
    height=280,
    tab_height=30,
    tab_position=230,
    tab_width=80,
    thickness=10
)

anode_active_material = ocd.AnodeMaterial.from_database("Synthetic Graphite")

anode_formulation = ocd.AnodeFormulation(
    active_materials={anode_active_material: 95},
    binders={binder: 2.5},
    conductive_additives={conductive_additive: 2.5}
)

my_anode = ocd.Anode(
    formulation=anode_formulation,
    current_collector=anode_current_collector,
    calender_density=1.4,
    mass_loading=9
)
# %% [markdown]
# %%
# create the layup

separator = ocd.Separator(
    material=separator_material,
    thickness=12,
    width=280,
    length=300
)

separator.areal_cost = 0.2

my_layup = ocd.ZFoldMonoLayer(
    cathode=my_cathode,
    anode=my_anode,
    separator=separator,
)

my_layup.np_ratio = 1.1

_plot_exporter.save(
    my_layup.plot_top_down_view(),
    'plot_top_down_view',
)
# %%
# create the stack assembly

my_stack = ocd.ZFoldStack(
    layup=my_layup,
    n_layers=40,
    additional_separator_wraps=3
)

# looks best in safari
_plot_exporter.save(
    my_stack.plot_side_view(),
    'plot_side_view',
)
# %%
# make the electrolyte

my_electrolyte = ocd.Electrolyte(
    name="1M NaPF6 in EC:PC:DMC (1:1:1 wt%)",
    density=1.2,
    specific_cost=2.5,
    color="#FF9D00"
)
# %%
# make the encapsulation

top_laminate = ocd.LaminateSheet(
    areal_cost=0.06,
    density=1.4,
    thickness=80
)

bottom_laminate = ocd.LaminateSheet(
    areal_cost=0.06,
    density=1.4,
    thickness=80
)

cathode_terminal_connector = ocd.PouchTerminal(
    material=prismatic_material,
    width=50,
    length=10,
    thickness=1
)

anode_terminal_connector = ocd.PouchTerminal(
    material=prismatic_material,
    width=50,
    length=10,
    thickness=1
)

encapsulation = ocd.PouchEncapsulation(
    top_laminate=top_laminate,
    bottom_laminate=bottom_laminate,
    cathode_terminal=cathode_terminal_connector,
    anode_terminal=anode_terminal_connector
)
# %%
# make the cell

cell = ocd.PouchCell(
    reference_electrode_assembly=my_stack,
    electrolyte=my_electrolyte,
    electrolyte_overfill=10,
    encapsulation=encapsulation,
    n_electrode_assembly=1,
    clipped_tab_length=10,
    name=cell_name,
    operating_voltage_window=(2.0, 4.1),
)

# looks better in safari
_plot_exporter.save(
    cell.plot_side_view(),
    'plot_side_view',
)
_plot_exporter.save(
    cell.plot_top_down_view(),
    'plot_top_down_view',
)
# %%
_plot_exporter.save(
    cell.plot_mass_breakdown(width=800, height=800),
    'plot_mass_breakdown',
)
# %%
_plot_exporter.save(
    cell.plot_cost_breakdown(width=800, height=800),
    'plot_cost_breakdown',
)
# %%
_plot_exporter.save(
    cell.plot_capacity_curve(width=1300, height=800),
    'plot_capacity_curve',
)
# %%
print(f"Cost ($): {cell.cost}")
print(f"Mass (g): {cell.mass}")
print(f"Energy Density (Wh/L): {cell.volumetric_energy}")
print(f"Energy (Wh): {cell.energy}")
print(f"Energy Density (Wh/kg): {cell.specific_energy}")
print(f"Normalized Cost ($/kWh): {cell.cost_per_energy}")
# %%
import pandas as pd
import datetime as dt
import re
from steer_opencell_design import __version__


db = DataManager()

db.remove_data(table_name=table_name, condition=f"name = '{cell.name}'")

# insert the cell into the database
db.insert_data(table_name=table_name, data=pd.DataFrame({
    'name': [cell.name],
    'object': [cell.serialize()],
    'form_factor': [cell.form_factor],
    'internal_construction': [cell.internal_construction],
    'date_created': [dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
    'version': [__version__],
    'chemistry': [cell.reference_chemistry]
}))

db.get_data(table_name)
# %%
size_mb = len(cell.serialize()) / (1024 ** 2)
print(f"{size_mb:.2f} MB")
