"""Optional PyTorch Geometric model definitions."""
from __future__ import annotations

try:
    import torch
    from torch import nn
    import torch.nn.functional as F
    from torch_geometric.nn import GATConv, GCNConv
except ImportError as exc:  # keep the core pipeline usable without optional GNN dependencies
    raise ImportError(
        "GNN support requires the optional dependencies. Install with: pip install -e '.[ml]'"
    ) from exc


class GCNClassifier(nn.Module):
    """Two-layer graph convolutional node classifier."""

    def __init__(self, input_dim: int, hidden_dim: int = 32, dropout: float = 0.25):
        super().__init__()
        self.conv1 = GCNConv(input_dim, hidden_dim)
        self.conv2 = GCNConv(hidden_dim, 2)
        self.dropout = dropout

    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = F.dropout(x, p=self.dropout, training=self.training)
        return self.conv2(x, edge_index)


class GATClassifier(nn.Module):
    """Graph attention node classifier with four attention heads."""

    def __init__(self, input_dim: int, hidden_dim: int = 32, dropout: float = 0.25):
        super().__init__()
        heads = 4
        head_dim = max(4, hidden_dim // heads)
        self.conv1 = GATConv(input_dim, head_dim, heads=heads, dropout=dropout)
        self.conv2 = GATConv(head_dim * heads, 2, heads=1, concat=False, dropout=dropout)
        self.dropout = dropout

    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index)
        x = F.elu(x)
        x = F.dropout(x, p=self.dropout, training=self.training)
        return self.conv2(x, edge_index)


def create_model(model_name: str, input_dim: int, hidden_dim: int = 32):
    """Instantiate a supported GNN architecture."""
    normalized = model_name.strip().lower()
    if normalized == "gcn":
        return GCNClassifier(input_dim, hidden_dim)
    if normalized == "gat":
        return GATClassifier(input_dim, hidden_dim)
    raise ValueError(f"Unsupported GNN model: {model_name}. Choose gcn or gat.")
