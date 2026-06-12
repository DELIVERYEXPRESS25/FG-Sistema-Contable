docker build --platform linux/amd64 -t jorlynvivas/apps:carlos_v1 .
docker push jorlynvivas/apps:carlos_v1     

docker run -d --name carlos_app -p 7000:5000 --restart always --cpus=1 --memory=1GB jorlynvivas/apps:carlos_v1