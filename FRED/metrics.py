# AUTOGENERATED! DO NOT EDIT! File to edit: 05f Metrics for Benchmarking.ipynb (unless otherwise specified).

__all__ = ['flow_neighbor_metric', 'silhouette_metric', 'nn_classification_metric', 'monotone_increasing_metric',
           'comprehensive_flow_metrics']

# Cell
import torch
import numpy as np
from .embed import flow_neighbor_loss
from .data_processing import flashlight_affinity_matrix, diffusion_map_from_affinities, flow_neighbors
import torch.nn.functional as F

def flow_neighbor_metric(X, flows, embedded_points, embedded_velocities):
    A = flashlight_affinity_matrix(X, flows, sigma = "automatic", flow_strength = 5)
    P_graph = F.normalize(A, p=1, dim=1)
    neighborhoods = flow_neighbors(num_nodes = len(X), P_graph = P_graph, n_neighbors = 5)
    row, col = neighborhoods
    directions = (embedded_points[col] - embedded_points[row])
    directions = F.normalize(torch.tensor(directions),dim=1)
    embedded_velocities = torch.tensor(embedded_velocities[row])
    embedded_velocities = F.normalize(embedded_velocities, dim=1)
    loss = torch.norm(directions - embedded_velocities)**2
    # neighbor_score = flow_neighbor_loss(neighborhoods, torch.tensor(embedded_points), torch.tensor(embedded_velocities))
    return loss

# Cell
import sklearn
def silhouette_metric(embedded_points, embedded_velocities, labels):
    points_and_flows = np.concatenate([embedded_points, embedded_velocities], axis=1)
    silhouette_points = sklearn.metrics.silhouette_score(embedded_points, labels)
    silhouette_points_and_flows = sklearn.metrics.silhouette_score(points_and_flows, labels)
    return silhouette_points, silhouette_points_and_flows

# Cell
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier

def nn_classification_metric(embedded_points, embedded_velocities, labels):
    points_and_flows = np.concatenate([embedded_points, embedded_velocities], axis=1)
    X_train, X_test, y_train, y_test = train_test_split(points_and_flows, labels, test_size=0.33, random_state=42)
    neighClass = KNeighborsClassifier(n_neighbors=3)
    neighClass.fit(X_train, y_train)
    knn_classifier_score = neighClass.score(X_test, y_test)
    return knn_classifier_score

# Cell
from .inference import diffusion_flow_integration
from tqdm.notebook import trange, tqdm
def monotone_increasing_metric(embedded_points, embedded_velocities, time_labels, num_samples = 1000, flow_strength=5):
    # sample random starting points
    idxs = torch.randint(len(embedded_points), size=[num_samples])
    neg_diffs = 0
    for pointA in tqdm(idxs):
        flowline = diffusion_flow_integration(torch.tensor(embedded_points), torch.tensor(embedded_velocities), starting_index = pointA, num_steps = 20, flow_strength=flow_strength)
        flowline = np.array(flowline)
        # take difference between neighbors in the vector
        times_at_flowline = time_labels[flowline]
        neighb_diffs = times_at_flowline[1:] - times_at_flowline[:-1]
        # print("neighb diffs: ",neighb_diffs)
        # get sums of negative numbers
        neg_diffs += (np.sum(neighb_diffs) - np.sum(np.abs(neighb_diffs)))/2
    neg_diffs/num_samples
    return neg_diffs

# Cell
import csv
def comprehensive_flow_metrics(X, flows, labels, embedded_points, embedded_velocities, time_labels, spreadsheet_name, unid, flow_strength):
    neighbor_score = flow_neighbor_metric(X, flows, embedded_points,embedded_velocities)
    silhouette_score, silhouete_score_with_flow = silhouette_metric(embedded_points, embedded_velocities, labels)
    knn_score = nn_classification_metric(embedded_points, embedded_velocities, labels)
    monotone_score = monotone_increasing_metric(embedded_points, embedded_velocities, time_labels)
    print(f"## SCORES ## \n silhouette score w/o flows: {silhouette_score}.\n silhouette score w/ flows:  {silhouete_score_with_flow} \n kNN Classifier {knn_score} \n Flow Neighbor Score {neighbor_score} \n Monotone Increasing Score {monotone_score}")
    return silhouette_score, silhouete_score_with_flow, knn_score, neighbor_score, monotone_score
