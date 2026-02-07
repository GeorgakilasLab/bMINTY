# Dockerfile
FROM node:20

# Set working directory
WORKDIR /app

# Accept build arguments for API configuration
ARG REACT_APP_API_BASE=http://localhost:8000/api
ENV REACT_APP_API_BASE=$REACT_APP_API_BASE

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy app files
COPY . .

# Expose port used by CRA dev server
EXPOSE 3000

# Start the dev server
CMD ["npm", "start"]
