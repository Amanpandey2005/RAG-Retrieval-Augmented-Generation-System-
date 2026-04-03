import axios from 'axios';

const API_URL = import.meta.env.PROD ? '' : 'http://localhost:8000';

export const api = {
  ingestText: async (text, title) => {
    const response = await axios.post(`${API_URL}/ingest`, { text, title });
    return response.data;
  },

  ingestFile: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await axios.post(`${API_URL}/ingest/file`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  query: async (query) => {
    const response = await axios.post(`${API_URL}/query`, { query });
    return response.data;
  }
};
