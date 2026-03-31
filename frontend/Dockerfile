# 第一阶段：构建环境
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# 第二阶段：生产运行环境
FROM nginx:stable-alpine
# 将构建后的静态文件拷贝到 Nginx 目录
COPY --from=build /app/dist /usr/share/nginx/html
# 暴露 Nginx 默认端口
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]