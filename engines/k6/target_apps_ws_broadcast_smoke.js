import ws from 'k6/ws';
import { check } from 'k6';

export const options = {
  vus: 1,
  iterations: 2,
};

const BASE_URL = __ENV.TARGET_URL || 'http://127.0.0.1:18088';
const WS_URL = BASE_URL.replace(/^http/, 'ws');
const ROOM = __ENV.WS_ROOM || 'smoke-room';
const MESSAGE = __ENV.WS_MESSAGE || 'smoke-broadcast';

export default function () {
  const response = ws.connect(
    `${WS_URL}/ws/broadcast/${ROOM}?client_id=publisher&deterministic=true`,
    { timeout: '5s' },
    (socket) => {
      let sawWelcome = false;
      let sawBroadcast = false;
      socket.on('message', (message) => {
        if (message.includes('"event":"welcome"')) {
          sawWelcome = true;
          socket.send(MESSAGE);
          return;
        }
        if (message.includes('"event":"broadcast"')) {
          sawBroadcast = message.includes(`"message":"${MESSAGE}"`) && message.includes(`"room":"${ROOM}"`);
          socket.close();
        }
      });
      socket.setTimeout(() => socket.close(), 3000);
      socket.on('close', () => {
        check({ sawWelcome, sawBroadcast }, {
          'ws broadcast welcome received': (state) => state.sawWelcome,
          'ws broadcast message received': (state) => state.sawBroadcast,
        });
      });
    }
  );

  check(response, {
    'ws broadcast handshake status is 101': (r) => r && r.status === 101,
  });
}
