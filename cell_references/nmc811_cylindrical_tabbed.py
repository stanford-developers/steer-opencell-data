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
cell_name = "NMC811 Cylindrical Tabbed Cell"

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
prismatic_material = ocd.PrismaticContainerMaterial.from_database("Aluminum")
# %%
conductive_additive.mass = 100
conductive_additive.cost
# %%
# Create the cathode

cathode_current_collector_material = ocd.CurrentCollectorMaterial.from_database('Aluminum')

tab = ocd.WeldTab(
    material=cathode_current_collector_material,
    width=15,
    length=120,
    thickness=13.5
)

cathode_current_collector = ocd.TabWeldedCurrentCollector(
    material=cathode_current_collector_material,
    width=130,
    length=3200,
    thickness=13.5,
    weld_tab=tab,
    tab_overhang=10,
    skip_coat_width=25,
    weld_tab_positions=[50, 1550, 3050]
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
    mass_loading=15
)

_plot_exporter.save(
    my_cathode.plot_top_down_view(),
    'plot_top_down_view',
)
# %%
# Create the anode

anode_current_collector_material = ocd.CurrentCollectorMaterial.from_database('Copper')

anode_current_collector = ocd.TabWeldedCurrentCollector(
    material=anode_current_collector_material,
    width=130,
    length=3200,
    thickness=8,
    weld_tab=tab,
    tab_overhang=10,
    skip_coat_width=25,
    weld_tab_positions=[750, 2250]
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
    mass_loading=10
)

_plot_exporter.save(
    my_anode.plot_top_down_view(),
    'plot_top_down_view',
)
# %%
# create the layup

top_separator = ocd.Separator(
    material=separator_material,
    thickness=12,
    width = 127,
    length = 3600
)

bottom_separator = ocd.Separator(
    material=separator_material,
    thickness=12,
    width = 127,
    length = 3600,
)

top_separator.areal_cost = 0.2
bottom_separator.areal_cost = 0.2

my_layup = ocd.Laminate(
    anode=my_anode,
    cathode=my_cathode,
    top_separator=top_separator,
    bottom_separator=bottom_separator
)

my_layup.np_ratio = 1.1

_plot_exporter.save(
    my_layup.plot_top_down_view(),
    'plot_top_down_view',
)
# %%
# create the jellyroll assembly

mandrel = ocd.RoundMandrel(
    diameter=5,
    length=500,
)


tape = ocd.Tape(
    material = tape_material,
    thickness=30,
    width=130
)

my_jellyroll = ocd.WoundJellyRoll(
    laminate=my_layup,
    mandrel=mandrel,
    tape=tape,
    additional_tape_wraps=3,
    collector_tab_crumple_factor=80
)
# %%
# make the encapsulation

cathode_terminal_connector = ocd.CylindricalTerminalConnector(
    material=prismatic_material,
    radius=16,
    thickness=3,
    fill_factor=0.7
)

anode_terminal_connector = ocd.CylindricalTerminalConnector(
    material=prismatic_material,
    radius=16,
    thickness=3,
    fill_factor=0.7
)

lid_assembly = ocd.CylindricalLidAssembly(
    material=prismatic_material,
    thickness=6,
    fill_factor=0.7,
)

canister = ocd.CylindricalCanister(
    material=prismatic_material,
    outer_radius=my_jellyroll.radius + 0.3,
    wall_thickness=0.2,
    height = my_jellyroll.total_height + lid_assembly.thickness + cathode_terminal_connector.thickness + anode_terminal_connector.thickness # this will autosize the canister. Replace this with the measured number from the teardown
)

container = ocd.CylindricalEncapsulation(
    canister=canister,
    lid_assembly=lid_assembly,
    cathode_terminal_connector=cathode_terminal_connector,
    anode_terminal_connector=anode_terminal_connector
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
# make the cell

cell = ocd.CylindricalCell(
    reference_electrode_assembly=my_jellyroll,
    encapsulation=container,
    electrolyte=my_electrolyte,
    operating_voltage_window=(2.0, 4.1),
    name=cell_name
)
# %%
_plot_exporter.save(
    cell.plot_cross_section(height=1200, width=1200),
    'plot_cross_section',
)
# %%
_plot_exporter.save(
    cell.plot_top_down_view(height=1200, width=1200),
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
cell.reference_electrode_assembly.layup.np_ratio
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

db.create_table(
    table_name=table_name,
    columns={
        'name': 'TEXT',
        'object': 'TEXT',
        'form_factor': 'TEXT',
        'internal_construction': 'TEXT',
        'date_created': 'TEXT',
        'version': 'TEXT',
        'chemistry': 'TEXT'
    }
)

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
db.get_table_names()
# %%
size_mb = len(cell.serialize()) / (1024 ** 2)
print(f"{size_mb:.2f} MB")
