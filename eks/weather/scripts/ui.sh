#!/bin/bash

kubectl  port-forward svc/${KUBERNETES_APP_WEATHER_AGENT_UI_NAME} \
  --namespace ${KUBERNETES_APP_WEATHER_AGENT_UI_NAMESPACE} \
8000:fastapi
