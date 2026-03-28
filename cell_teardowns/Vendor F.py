# %%
from steer_opencell_data.script_utils import build_plot_exporter

_plot_exporter = build_plot_exporter(__file__)
# %%
from steer_opencell_data.DataManager import DataManager
import steer_opencell_design as ocd
# %%
# User Inputs

####################

table_name = 'teardowns' #### change this to cell_teardowns for teardowns
cell_name = "Vendor F NFM"

#####################
# %%
import os
os.environ["OPENCELL_ENV"] = "development"
# %%
# set some standard materials

conductive_additive = ocd.ConductiveAdditive.from_database("Super P")
binder = ocd.Binder.from_database("PVDF")
insulation = ocd.InsulationMaterial.from_database("Aluminium Oxide, 95%")
current_collector_material = ocd.CurrentCollectorMaterial.from_database('Aluminum')
separator_material = ocd.SeparatorMaterial.from_database('Polyethylene')
tape_material = ocd.TapeMaterial.from_database("Kapton")
prismatic_material = ocd.PrismaticContainerMaterial.from_database("Aluminum")
# %%
# Create the cathode

cathode_current_collector=ocd.PunchedCurrentCollector(
    material=current_collector_material,
    width=166,
    height=190,
    tab_height=20,
    tab_position=45,
    tab_width=35,
    thickness=12,
    insulation_width=2
)

cathode_active_material = ocd.CathodeMaterial.from_database("NFM111 (Vendor B)")

cathode_formulation = ocd.CathodeFormulation(
    active_materials={cathode_active_material: 97},
    binders={binder: 1.5},
    conductive_additives={conductive_additive: 1.5}
)

my_cathode = ocd.Cathode(
    formulation=cathode_formulation,
    current_collector=cathode_current_collector,
    calender_density=2.71,
    mass_loading=19,
    insulation_material=insulation,
    insulation_thickness=3
)
# %%
# Create the anode

anode_current_collector = ocd.PunchedCurrentCollector(
    material=current_collector_material,
    width=168,
    height=190,
    tab_height=20,
    tab_position=125,
    tab_width=35,
    thickness=12
)

anode_active_material = ocd.AnodeMaterial.from_database("Hard Carbon (Vendor D)")

anode_formulation = ocd.AnodeFormulation(
    active_materials={anode_active_material: 95},
    binders={binder: 2.5},
    conductive_additives={conductive_additive: 2.5}
)

my_anode = ocd.Anode(
    formulation=anode_formulation,
    current_collector=anode_current_collector,
    calender_density=1.02,
    mass_loading=8.87
)
# %%
# create the layup

separator = ocd.Separator(
    material=separator_material,
    thickness=12,
    width = 194,
)

my_layup = ocd.ZFoldMonoLayer(
    cathode=my_cathode,
    anode=my_anode,
    separator=separator,
    electrode_orientation='longitudinal'
)

_plot_exporter.save(
    my_layup.plot_top_down_view(),
    'plot_top_down_view',
)
# %%
# create the stack assembly

my_stack = ocd.ZFoldStack(
    layup=my_layup,
    n_layers=94,
    additional_separator_wraps=3
)

_plot_exporter.save(
    my_stack.plot_side_view(),
    'plot_side_view',
)
# %%
# make the electrolyte

my_electrolyte = ocd.Electrolyte(
    name="1M NaPF6 in EC:PC:DMC (1:1:1 wt%)",
    density=1.2,
    specific_cost=5.7,
    color="#FF9D00"
)
# %%
# make the encapsulation

cathode_terminal_connector = ocd.PrismaticTerminalConnector(
    material=prismatic_material,
    thickness=1,
    width=40,
    length=40
)

anode_terminal_connector = ocd.PrismaticTerminalConnector(
    material=prismatic_material,
    thickness=1,
    width=40,
    length=40
)

lid_assembly = ocd.PrismaticLidAssembly(
    material=prismatic_material,
    thickness=3,
)

canister = ocd.PrismaticCanister(
    material=prismatic_material,
    width=174,
    length=71.5,
    height=205,
    wall_thickness=1.5
)

my_encapsulation = ocd.PrismaticEncapsulation(
    canister=canister,
    cathode_terminal_connector=cathode_terminal_connector,
    anode_terminal_connector=anode_terminal_connector,
    lid_assembly=lid_assembly,
    connector_orientation='longitudinal'
)
# %%
# make the cell

cell = ocd.PrismaticCell(
    reference_electrode_assembly=my_stack,
    electrolyte=my_electrolyte,
    electrolyte_overfill=7,
    encapsulation=my_encapsulation,
    n_electrode_assembly=2,
    clipped_tab_length=4,
    operating_voltage_window=(1.5, 3.96),
    name=cell_name
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
