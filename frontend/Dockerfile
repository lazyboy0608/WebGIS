# ============================================================
# Stage 1: Build Frontend Artifacts (Vite + React)
# ============================================================
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies with clean cache
COPY package*.json ./
RUN npm ci

# Copy source and build static bundle
COPY . .
RUN npm run build

# ============================================================
# Stage 2: Production Nginx Server (Single Gateway)
# ============================================================
FROM nginx:1.25-alpine AS runner

# Remove default Nginx welcome assets
RUN rm -rf /usr/share/nginx/html/* /etc/nginx/conf.d/default.conf

# Copy compiled static assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx routing and proxy configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
