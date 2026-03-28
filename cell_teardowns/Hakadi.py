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
cell_name = "Hakadi NFM"

#####################
# %%
import os
os.environ["OPENCELL_ENV"] = "development"
# %%
# Get current collector materials from the database
current_collector_material = ocd.CurrentCollectorMaterial.from_database('Aluminum')
conductive_additive = ocd.ConductiveAdditive.from_database("Super P")
binder = ocd.Binder.from_database("PVDF")
insulation_material = ocd.InsulationMaterial.from_database("Aluminium Oxide, 95%")
separator_material = ocd.SeparatorMaterial.from_database("Polypropylene")
tape_material = ocd.TapeMaterial.from_database("Kapton")

my_electrolyte = ocd.Electrolyte(
    name="Electrolyte",
    density=1.18,
    specific_cost=10,
    color="#FFBE55"
)
# %%
tab = ocd.WeldTab(
    material=current_collector_material,
    width=5,
    length=30,
    thickness=0.5
)
# %%
# Create the cathode

cathode_current_collector = ocd.TabWeldedCurrentCollector(
    material=current_collector_material,
    width=57.5,
    length=565,
    thickness=13,
    weld_tab=tab,
    weld_tab_positions=[250],
    skip_coat_width=5,
    tab_overhang=5
)

cathode_active_material = ocd.CathodeMaterial.from_database("NFM111 (Vendor B)")
cathode_active_material.irreversible_specific_capacity = 148

cathode_formulation = ocd.CathodeFormulation(
    active_materials={cathode_active_material: 97},
    binders={binder: 1.5},
    conductive_additives={conductive_additive: 1.5}
)

my_cathode = ocd.Cathode(
    formulation=cathode_formulation,
    current_collector=cathode_current_collector,
    calender_density=2.64,
    mass_loading=17.57,
)
# %%
# Create the anode

anode_current_collector = ocd.TabWeldedCurrentCollector(
    material=current_collector_material,
    width=59,
    length=653,
    thickness=13,
    weld_tab=tab,
    weld_tab_positions=[150, 400],
    skip_coat_width=5,
    tab_overhang=5,
)

anode_active_material = ocd.AnodeMaterial.from_database("Hard Carbon (Vendor D)")
anode_active_material.irreversible_specific_capacity = 290


anode_formulation = ocd.AnodeFormulation(
    active_materials={anode_active_material: 95},
    binders={binder: 3.5},
    conductive_additives={conductive_additive: 1.5}
)

my_anode = ocd.Anode(
    formulation=anode_formulation,
    current_collector=anode_current_collector,
    calender_density=0.95,
    mass_loading=9.38,
)
# %%
# make the layup

top_separator = ocd.Separator(
    material=separator_material,
    width=61,
    length=750,
    thickness=11
)

bottom_separator = ocd.Separator(
    material=separator_material,
    width=61,
    length=750,
    thickness=11
)

top_separator.areal_cost = 0.2
bottom_separator.areal_cost = 0.2

my_layup = ocd.Laminate(
    anode=my_anode,
    cathode=my_cathode,
    top_separator=top_separator,
    bottom_separator=bottom_separator
)
# %%
# create the jellyroll assembly
mandrel = ocd.RoundMandrel(
    diameter=3.5,
    length=55,
)

tape = ocd.Tape(
    material = tape_material,
    thickness=30
)

my_jellyroll = ocd.WoundJellyRoll(
    laminate=my_layup,
    mandrel=mandrel,
    tape=tape,
    additional_tape_wraps=4,
    name="Hakadi NFM",
)

_plot_exporter.save(
    my_layup.plot_top_down_view(opacity=0.5),
    'plot_top_down_view',
)
print(my_layup.np_ratio)
# %%
_plot_exporter.save(
    my_jellyroll.plot_mass_breakdown(height=800),
    'plot_mass_breakdown',
)
# %%
_plot_exporter.save(
    my_jellyroll.plot_cost_breakdown(height=800),
    'plot_cost_breakdown',
)
# %%
my_jellyroll.diameter
# %%
_plot_exporter.save(
    my_jellyroll.plot_spiral(height=1300, width=1300),
    'plot_spiral',
)
# %%
_plot_exporter.save(
    my_jellyroll.plot_capacity_curve(height=800, width=800),
    'plot_capacity_curve',
)
# %%
my_cathode_terminal_connector = ocd.CylindricalTerminalConnector(
    material=ocd.PrismaticContainerMaterial.from_database('Aluminum'),
    thickness=1,
    radius=8.5,
    fill_factor=0.4,
)

my_anode_terminal_connector = ocd.CylindricalTerminalConnector(
    material=ocd.PrismaticContainerMaterial.from_database('Aluminum'),
    thickness=1,
    radius=8.5,
    fill_factor=0.4,
)

my_lid = ocd.CylindricalLidAssembly(
        material= ocd.PrismaticContainerMaterial.from_database('Steel'),
        thickness= 1,
        radius= 8.5,
        fill_factor= 0.2,
)

my_canister = ocd.CylindricalCanister(
    material= ocd.PrismaticContainerMaterial.from_database('Steel'),
    outer_radius= 18/2,
    height=65,
    wall_thickness= 0.2,
)
# %%
my_cylindtrical_encapsulation = ocd.CylindricalEncapsulation(
    cathode_terminal_connector=my_cathode_terminal_connector,
    anode_terminal_connector=my_anode_terminal_connector,
    lid_assembly=my_lid,
    canister=my_canister
)
# %%
cell = ocd.CylindricalCell(
    reference_electrode_assembly=my_jellyroll,
    encapsulation=my_cylindtrical_encapsulation,
    electrolyte=my_electrolyte,
    operating_voltage_window= (1.5, 4.1),
    electrolyte_overfill = 20,
    name= cell_name,
)
# %%
_plot_exporter.save(
    cell.plot_top_down_view(height=800, width=800),
    'plot_top_down_view',
)
# %%
_plot_exporter.save(
    cell.plot_cross_section(height=800, width=800),
    'plot_cross_section',
)
# %%
_plot_exporter.save(
    cell.plot_mass_breakdown(),
    'plot_mass_breakdown',
)
# %%
_plot_exporter.save(
    cell.plot_capacity_curve(height=800, width=1000),
    'plot_capacity_curve',
)
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
# %%
