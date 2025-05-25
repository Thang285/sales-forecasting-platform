![alt text](image.png)

to use:

1. Run ./setup.sh
2. kubectl port-forward svc/forecasting-api-service 8000:80
3. kubectl port-forward svc/streamlit-dashboard-service 8501:80
5. cloudflared tunnel run streamlit-dashboard 