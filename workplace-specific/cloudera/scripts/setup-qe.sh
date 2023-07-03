#!/usr/bin/env bash

function kubeconf-qe() {
    export KUBECONFIG=$HOME/.kube/ocp-qaas-prod-qe.conf
    echo "KUBECONFIG=$KUBECONFIG"
}

function kubeconf-qaas() {
    export KUBECONFIG=$HOME/.kube/rke-qaas-prod-qe.conf
    echo "KUBECONFIG=$KUBECONFIG"
}