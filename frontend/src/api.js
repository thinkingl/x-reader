import axios from 'axios';

const getBaseURL = () => {
  const { protocol, hostname } = window.location;
  return `${protocol}//${hostname}:8000`;
};

const api = axios.create({
  baseURL: getBaseURL(),
  timeout: 30000,
});

export default api;
