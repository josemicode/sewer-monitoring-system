import axios from 'axios';

const API_URL = `http://${window.location.hostname}:8000`;

const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export const loginUser = async (username, password) => {
    const response = await api.post('/login', { username, password });
    return response.data;
};

export const getHistoryAggregated = async (startDate, aggregation = 'hour') => {
    const response = await api.get('/history/aggregated', {
        params: { start_date: startDate, aggregation },
    });
    return response.data;
};

export const getHistoryRaw = async (sensorId, startDate) => {
    const response = await api.get('/history/raw', {
        params: { sensor_id: sensorId, start_date: startDate },
    });
    return response.data;
};

export const acknowledgeAlarm = async (alarmId) => {
    const response = await api.post(`/acknowledge/${alarmId}`);
    return response.data;
};

export default api;
