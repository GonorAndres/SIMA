import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
  // Cloud Run escala a cero: el primer request de una visita paga el arranque
  // en frio (medido en 6.3 s). Sin timeout explicito axios espera de forma
  // indefinida, asi que un backend caido deja paneles en blanco para siempre.
  // 30 s deja holgura de sobra sobre el arranque en frio y aun asi falla lo
  // bastante pronto como para que la UI muestre ErrorState con reintento.
  timeout: 30000,
});

export default api;
