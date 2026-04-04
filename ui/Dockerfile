FROM node:20-alpine

WORKDIR /app/ui

COPY ui/package*.json ./
RUN npm ci

COPY ui ./

ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_API_FALLBACK_MODE=live

ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_API_FALLBACK_MODE=${VITE_API_FALLBACK_MODE}

RUN npm run build

EXPOSE 5173

CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "5173"]
