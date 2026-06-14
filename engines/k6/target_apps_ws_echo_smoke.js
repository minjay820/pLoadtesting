import ws from 'k6/ws';
import { check } from 'k6';

export const options = {
  vus: 1,
  iterations: 2,
};

const BASE_URL = __ENV.TARGET_URL || 'http://127.0.0.1:18088';
const WS_URL = BASE_URL.replace(/^http/, 'ws');
const WS_PATH = __ENV.WS_PATH || '/ws/echo';
const WS_MESSAGE = __ENV.WS_MESSAGE || 'smoke-echo';

export default function () {
  const response = ws.connect(`${WS_URL}${WS_PATH}?deterministic=true`, { timeout: '5s' }, (socket) => {
    let sawWelcome = false;
    let sawEcho = false;

    socket.on('message', (message) => {
      if (message.includes('"event":"welcome"')) {
        sawWelcome = true;
        socket.send(WS_MESSAGE);
        return;
      }
      if (message.includes('"event":"echo"')) {
        sawEcho = message.includes(`"message":"${WS_MESSAGE}"`) && message.includes('"sequence":1');
        socket.close();
      }
    });

    socket.setTimeout(() => socket.close(), 3000);

    socket.on('close', () => {
      check({ sawWelcome, sawEcho }, {
        'ws echo welcome received': (state) => state.sawWelcome,
        'ws echo response received': (state) => state.sawEcho,
      });
    });
  });

  check(response, {
    'ws echo handshake status is 101': (r) => r && r.status === 101,
  });
}
