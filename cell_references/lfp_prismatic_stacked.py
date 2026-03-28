# %%
from steer_opencell_data.script_utils import build_plot_exporter

_plot_exporter = build_plot_exporter(__file__)
# %%
from steer_opencell_data.DataManager import DataManager
import steer_opencell_design as ocd
# %%
import os
os.environ["OPENCELL_ENV"] = "development"
# %%
# User Inputs

####################

table_name = 'cell_references' #### change this to cell_teardowns for teardowns
cell_name = "LFP Stacked Prismatic Cell"

#####################
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

cathode_active_material = ocd.CathodeMaterial.from_database("LFP")

cathode_formulation = ocd.CathodeFormulation(
    active_materials={cathode_active_material: 95},
    binders={binder: 2.5},
    conductive_additives={conductive_additive: 2.5}
)

my_cathode = ocd.Cathode(
    formulation=cathode_formulation,
    current_collector=cathode_current_collector,
    calender_density=2.6,
    mass_loading=18,
    insulation_material=insulation,
    insulation_thickness=3
)
# %%
# Create the anode

cathode_current_collector_material = ocd.CurrentCollectorMaterial.from_database("Copper")

anode_current_collector = ocd.PunchedCurrentCollector(
    material=cathode_current_collector_material,
    width=302,
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
    width = 290,
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

cathode_terminal_connector = ocd.PrismaticTerminalConnector(
    material=prismatic_material,
    thickness=2,
    width=40,
    length=40
)

anode_terminal_connector = ocd.PrismaticTerminalConnector(
    material=prismatic_material,
    thickness=2,
    width=40,
    length=40
)

lid_assembly = ocd.PrismaticLidAssembly(
    material=prismatic_material,
    thickness=8,
)

canister = ocd.PrismaticCanister(
    material=prismatic_material,
    width=310,
    length=56,
    height=300,
    wall_thickness=1
)

my_encapsulation = ocd.PrismaticEncapsulation(
    canister=canister,
    cathode_terminal_connector=cathode_terminal_connector,
    anode_terminal_connector=anode_terminal_connector,
    lid_assembly=lid_assembly,
)
# %%
# make the cell

cell = ocd.PrismaticCell(
    reference_electrode_assembly=my_stack,
    electrolyte=my_electrolyte,
    electrolyte_overfill=10,
    encapsulation=my_encapsulation,
    n_electrode_assembly=4,
    clipped_tab_length=4,
    name=cell_name,
    operating_voltage_window=(2, 3.65)
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
