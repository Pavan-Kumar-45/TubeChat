import axios from 'axios';

const API_URL = 'http://127.0.0.1:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      // window.location.href = '/login'; 
      // Handle redirect in context or component to avoid loops
    }
    return Promise.reject(error);
  }
);

export const authService = {
  login: async (username, password) => {
    const response = await api.post('/auth/token', { username, password });
    return response.data;
  },
  register: async (username, password) => {
    const response = await api.post('/auth/register', { username, password });
    return response.data;
  },
  getCurrentUser: async () => {
    const response = await api.get('/user/me');
    return response.data;
  },
};

export const chatService = {
  createChat: async (url, name) => {
    const response = await api.post('/chat/create', { url, name });
    return response.data;
  },
  getUserChats: async () => {
    const response = await api.get('/chat/list');
    return response.data;
  },
  getChat: async (chatId) => {
    const response = await api.get(`/chat/${chatId}`);
    return response.data;
  },
  sendMessage: async (chatId, message) => {
    const response = await api.post(`/chat/${chatId}/message`, { question: message });
    return response.data;
  },
  deleteChat: async (chatId) => {
    const response = await api.delete(`/user/chats/${chatId}`);
    return response.data;
  },
};

export default api;
