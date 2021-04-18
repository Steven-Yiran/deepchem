from typing import List, Tuple
import numpy as np

from deepchem.utils.typing import RDKitAtom, RDKitBond, RDKitMol
from deepchem.feat.graph_data import GraphData
from deepchem.feat.base_classes import MolecularFeaturizer
from deepchem.utils.molecule_feature_utils import get_atom_type_one_hot
from deepchem.utils.molecule_feature_utils import construct_hydrogen_bonding_info
from deepchem.utils.molecule_feature_utils import get_atom_hydrogen_bonding_one_hot
from deepchem.utils.molecule_feature_utils import get_atom_hybridization_one_hot
from deepchem.utils.molecule_feature_utils import get_atom_total_num_Hs_one_hot
from deepchem.utils.molecule_feature_utils import get_atom_is_in_aromatic_one_hot
from deepchem.utils.molecule_feature_utils import get_atom_chirality_one_hot
from deepchem.utils.molecule_feature_utils import get_atom_formal_charge
from deepchem.utils.molecule_feature_utils import get_atom_partial_charge
from deepchem.utils.molecule_feature_utils import get_atom_total_degree_one_hot
from deepchem.utils.molecule_feature_utils import get_bond_type_one_hot
from deepchem.utils.molecule_feature_utils import get_bond_is_in_same_ring_one_hot
from deepchem.utils.molecule_feature_utils import get_bond_is_conjugated_one_hot
from deepchem.utils.molecule_feature_utils import get_bond_stereo_one_hot


def _construct_atom_feature(
    atom: RDKitAtom, h_bond_infos: List[Tuple[int, str]], use_chirality: bool,
    use_partial_charge: bool) -> np.ndarray:
  """Construct an atom feature from a RDKit atom object.

  Parameters
  ----------
  atom: rdkit.Chem.rdchem.Atom
    RDKit atom object
  h_bond_infos: List[Tuple[int, str]]
    A list of tuple `(atom_index, hydrogen_bonding_type)`.
    Basically, it is expected that this value is the return value of
    `construct_hydrogen_bonding_info`. The `hydrogen_bonding_type`
    value is "Acceptor" or "Donor".
  use_chirality: bool
    Whether to use chirality information or not.
  use_partial_charge: bool
    Whether to use partial charge data or not.

  Returns
  -------
  np.ndarray
    A one-hot vector of the atom feature.
  """
  atom_type = get_atom_type_one_hot(atom)
  formal_charge = get_atom_formal_charge(atom)
  hybridization = get_atom_hybridization_one_hot(atom)
  acceptor_donor = get_atom_hydrogen_bonding_one_hot(atom, h_bond_infos)
  aromatic = get_atom_is_in_aromatic_one_hot(atom)
  degree = get_atom_total_degree_one_hot(atom)
  total_num_Hs = get_atom_total_num_Hs_one_hot(atom)
  atom_feat = np.concatenate([
      atom_type, formal_charge, hybridization, acceptor_donor, aromatic, degree,
      total_num_Hs
  ])

  if use_chirality:
    chirality = get_atom_chirality_one_hot(atom)
    atom_feat = np.concatenate([atom_feat, chirality])

  if use_partial_charge:
    partial_charge = get_atom_partial_charge(atom)
    atom_feat = np.concatenate([atom_feat, partial_charge])
  return atom_feat


def _construct_bond_feature(bond: RDKitBond) -> np.ndarray:
  """Construct a bond feature from a RDKit bond object.

  Parameters
  ---------
  bond: rdkit.Chem.rdchem.Bond
    RDKit bond object

  Returns
  -------
  np.ndarray
    A one-hot vector of the bond feature.
  """
  bond_type = get_bond_type_one_hot(bond)
  same_ring = get_bond_is_in_same_ring_one_hot(bond)
  conjugated = get_bond_is_conjugated_one_hot(bond)
  stereo = get_bond_stereo_one_hot(bond)
  return np.concatenate([bond_type, same_ring, conjugated, stereo])


class MolGraphConvFeaturizer(MolecularFeaturizer):
  """This class is a featurizer of general graph convolution networks for molecules.

  The default node(atom) and edge(bond) representations are based on
  `WeaveNet paper <https://arxiv.org/abs/1603.00856>`_. If you want to use your own representations,
  you could use this class as a guide to define your original Featurizer. In many cases, it's enough
  to modify return values of `construct_atom_feature` or `construct_bond_feature`.

  The default node representation are constructed by concatenating the following values,
  and the feature length is 30.

  - Atom type: A one-hot vector of this atom, "C", "N", "O", "F", "P", "S", "Cl", "Br", "I", "other atoms".
  - Formal charge: Integer electronic charge.
  - Hybridization: A one-hot vector of "sp", "sp2", "sp3".
  - Hydrogen bonding: A one-hot vector of whether this atom is a hydrogen bond donor or acceptor.
  - Aromatic: A one-hot vector of whether the atom belongs to an aromatic ring.
  - Degree: A one-hot vector of the degree (0-5) of this atom.
  - Number of Hydrogens: A one-hot vector of the number of hydrogens (0-4) that this atom connected.
  - Chirality: A one-hot vector of the chirality, "R" or "S". (Optional)
  - Partial charge: Calculated partial charge. (Optional)

  The default edge representation are constructed by concatenating the following values,
  and the feature length is 11.

  - Bond type: A one-hot vector of the bond type, "single", "double", "triple", or "aromatic".
  - Same ring: A one-hot vector of whether the atoms in the pair are in the same ring.
  - Conjugated: A one-hot vector of whether this bond is conjugated or not.
  - Stereo: A one-hot vector of the stereo configuration of a bond.

  If you want to know more details about features, please check the paper [1]_ and
  utilities in deepchem.utils.molecule_feature_utils.py.

  Examples
  --------
  >>> smiles = ["C1CCC1", "C1=CC=CN=C1"]
  >>> featurizer = MolGraphConvFeaturizer(use_edges=True)
  >>> out = featurizer.featurize(smiles)
  >>> type(out[0])
  <class 'deepchem.feat.graph_data.GraphData'>
  >>> out[0].num_node_features
  30
  >>> out[0].num_edge_features
  11

  References
  ----------
  .. [1] Kearnes, Steven, et al. "Molecular graph convolutions: moving beyond fingerprints."
     Journal of computer-aided molecular design 30.8 (2016):595-608.

  Note
  ----
  This class requires RDKit to be installed.
  """

  def __init__(self,
               use_edges: bool = False,
               use_chirality: bool = False,
               use_partial_charge: bool = False):
    """
    Parameters
    ----------
    use_edges: bool, default False
      Whether to use edge features or not.
    use_chirality: bool, default False
      Whether to use chirality information or not.
      If True, featurization becomes slow.
    use_partial_charge: bool, default False
      Whether to use partial charge data or not.
      If True, this featurizer computes gasteiger charges.
      Therefore, there is a possibility to fail to featurize for some molecules
      and featurization becomes slow.
    """
    self.use_edges = use_edges
    self.use_partial_charge = use_partial_charge
    self.use_chirality = use_chirality

  def _featurize(self, mol: RDKitMol) -> GraphData:
    """Calculate molecule graph features from RDKit mol object.

    Parameters
    ----------
    mol: rdkit.Chem.rdchem.Mol
      RDKit mol object.

    Returns
    -------
    graph: GraphData
      A molecule graph with some features.
    """
    if self.use_partial_charge:
      try:
        mol.GetAtomWithIdx(0).GetProp('_GasteigerCharge')
      except:
        # If partial charges were not computed
        try:
          from rdkit.Chem import AllChem
          AllChem.ComputeGasteigerCharges(mol)
        except ModuleNotFoundError:
          raise ImportError("This class requires RDKit to be installed.")

    # construct atom (node) feature
    h_bond_infos = construct_hydrogen_bonding_info(mol)
    atom_features = np.asarray(
        [
            _construct_atom_feature(atom, h_bond_infos, self.use_chirality,
                                    self.use_partial_charge)
            for atom in mol.GetAtoms()
        ],
        dtype=float,
    )

    # construct edge (bond) index
    src, dest = [], []
    for bond in mol.GetBonds():
      # add edge list considering a directed graph
      start, end = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
      src += [start, end]
      dest += [end, start]

    # construct edge (bond) feature
    bond_features = None  # deafult None
    if self.use_edges:
      features = []
      for bond in mol.GetBonds():
        features += 2 * [_construct_bond_feature(bond)]
      bond_features = np.asarray(features, dtype=float)

    return GraphData(
        node_features=atom_features,
        edge_index=np.asarray([src, dest], dtype=int),
        edge_features=bond_features)


from deepchem.feat import MolecularFeaturizer
import numpy as np
from deepchem.feat.graph_data import GraphData


class PAGTNFeaturizer(MolecularFeaturizer):

  def __init__(self, max_length=5):

    try:
      from rdkit import Chem
      from dgllife.utils import ConcatFeaturizer
      from dgllife.utils import atom_formal_charge_one_hot, atom_type_one_hot, atom_degree_one_hot
      from dgllife.utils import atom_explicit_valence_one_hot, atom_implicit_valence_one_hot
      from dgllife.utils import atom_is_aromatic
      from functools import partial
      from dgllife.utils import one_hot_encoding
      from dgllife.utils import bond_type_one_hot, ConcatFeaturizer, bond_is_conjugated, bond_is_in_ring
    except:
      raise ImportError(
          "This class requires Rdkit & DGLLifeSci to be installed.")
    self.SYMBOLS = [
        'C', 'N', 'O', 'S', 'F', 'Si', 'P', 'Cl', 'Br', 'Mg', 'Na', 'Ca', 'Fe',
        'As', 'Al', 'I', 'B', 'V', 'K', 'Tl', 'Yb', 'Sb', 'Sn', 'Ag', 'Pd',
        'Co', 'Se', 'Ti', 'Zn', 'H', 'Li', 'Ge', 'Cu', 'Au', 'Ni', 'Cd', 'In',
        'Mn', 'Zr', 'Cr', 'Pt', 'Hg', 'Pb', 'W', 'Ru', 'Nb', 'Re', 'Te', 'Rh',
        'Tc', 'Ba', 'Bi', 'Hf', 'Mo', 'U', 'Sm', 'Os', 'Ir', 'Ce', 'Gd', 'Ga',
        'Cs', '*', 'UNK'
    ]

    self.RING_TYPES = [(5, False), (5, True), (6, False), (6, True)]
    self.ordered_pair = lambda a, b: (a, b) if a < b else (b, a)
    self.bond_featurizer = ConcatFeaturizer(
        [bond_type_one_hot, bond_is_conjugated, bond_is_in_ring])
    self.max_length = 5

  def PAGTNAtomFeaturizer(atom):
    atom_type = get_atom_type_one_hot(atom, self.SYMBOLS, False)
    formal_charge = get_atom_formal_charge(atom)
    degree = get_atom_total_degree_one_hot(atom, 10, False)
    exp_valence = atom_explicit_valence_one_hot(atom, list(range(7)), False)
    imp_valence = get_atom_implicit_valence_one_hot(atom, list(range(6)), False)
    armoticity = get_atom_is_in_aromatic_one_hot(atom)
    atom_feat = np.concatenate([
        atom_type, formal_charge, degree, exp_valence, imp_valence, armoticity
    ])
    return atom_feat

  def bond_features(self, mol, path_atoms, ring_info):
    """Computes the edge features for a given pair of nodes.
        Parameters
        ----------
        mol : rdkit.Chem.rdchem.Mol
            RDKit molecule instance.
        path_atoms: tuple
            Shortest path between the given pair of nodes.
        ring_info: list
            Different rings that contain the pair of atoms
        """
    features = []
    path_bonds = []
    path_length = len(path_atoms)
    for path_idx in range(path_length - 1):
      bond = mol.GetBondBetweenAtoms(path_atoms[path_idx],
                                     path_atoms[path_idx + 1])
      if bond is None:
        import warnings
        warnings.warn('Valid idx of bonds must be passed')
      path_bonds.append(bond)

    for path_idx in range(self.max_length):
      if path_idx < len(path_bonds):
        features.append(self.bond_featurizer(path_bonds[path_idx]))
      else:
        features.append([0, 0, 0, 0, 0, 0])

    if path_length + 1 > self.max_length:
      path_length = self.max_length + 1
    position_feature = np.zeros(self.max_length + 2)
    position_feature[path_length] = 1
    features.append(position_feature)
    if ring_info:
      rfeat = [
          one_hot_encoding(r, allowable_set=self.RING_TYPES) for r in ring_info
      ]
      rfeat = [True] + np.any(rfeat, axis=0).tolist()
      features.append(rfeat)
    else:
      # This will return a boolean vector with all entries False
      features.append(
          [False] + one_hot_encoding(ring_info, allowable_set=self.RING_TYPES))
    return np.concatenate(features, axis=0)

  def PAGTNBondFeaturizer(self, mol):
    """Featurizes the input molecule.
        Parameters
        ----------
        mol : rdkit.Chem.rdchem.Mol
            RDKit molecule instance.
        Returns
        -------
        dict
            Mapping _edge_data_field to a float32 tensor of shape (N, M), where
            N is the number of atom pairs and M is the feature size depending on max_length.
        """

    n_atoms = mol.GetNumAtoms()
    # To get the shortest paths between two nodes.
    paths_dict = utils.compute_all_pairs_shortest_path(mol)
    # To get info if two nodes belong to the same ring.
    rings_dict = utils.compute_pairwise_ring_info(mol)
    # Featurizer
    feats = []
    src = []
    dest = []
    for i in range(n_atoms):
      for j in range(n_atoms):
        src.append(i)
        dest.append(j)

        if (i, j) not in paths_dict:
          feats.append(np.zeros(7 * self.max_length + 7))
          continue
        ring_info = rings_dict.get(self.ordered_pair(i, j), [])
        feats.append(self.bond_features(mol, paths_dict[(i, j)], ring_info))

    return np.array([src, dest], dtype=np.int), np.array(feats, dtype=np.float)

  def _featurize(self, mol):
    node_features = self.PAGTNAtomFeaturizer(mol)
    edge_index, edge_features = self.PAGTNBondFeaturizer(mol)
    graph = GraphData(node_features, edge_index, edge_features)
    return graph
