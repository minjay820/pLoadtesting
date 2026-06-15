function numberFromEnv(name, fallback) {
  const value = __ENV[name];
  if (value === undefined || value === null || value === '') {
    return fallback;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function compactStages(stages) {
  return stages.filter((stage) => stage.duration !== '0s');
}

export function executionOptions(defaults) {
  const vus = defaults.vus || 1;
  const durationSeconds = numberFromEnv('DURATION_SECONDS', defaults.durationSeconds || 10);
  const rampUpSeconds = numberFromEnv('RAMP_UP_SECONDS', defaults.rampUpSeconds || 0);
  const rampDownSeconds = numberFromEnv('RAMP_DOWN_SECONDS', defaults.rampDownSeconds || 0);
  const gracefulStopSeconds = numberFromEnv('GRACEFUL_STOP_SECONDS', defaults.gracefulStopSeconds || 10);
  const iterationLimit = numberFromEnv('ITERATION_LIMIT', defaults.iterations || null);
  const dataPolicy = __ENV.DATA_POLICY || defaults.dataPolicy || 'duration_first';

  const options = {
    thresholds: defaults.thresholds || {},
  };

  if (iterationLimit && dataPolicy === 'iteration_first') {
    options.scenarios = {
      default: {
        executor: 'shared-iterations',
        vus,
        iterations: iterationLimit,
        maxDuration: `${durationSeconds + gracefulStopSeconds}s`,
        gracefulStop: `${gracefulStopSeconds}s`,
      },
    };
    return options;
  }

  if (rampUpSeconds > 0 || rampDownSeconds > 0) {
    options.scenarios = {
      default: {
        executor: 'ramping-vus',
        stages: compactStages([
          { duration: `${rampUpSeconds}s`, target: vus },
          { duration: `${durationSeconds}s`, target: vus },
          { duration: `${rampDownSeconds}s`, target: 0 },
        ]),
        gracefulStop: `${gracefulStopSeconds}s`,
      },
    };
    return options;
  }

  options.scenarios = {
    default: {
      executor: 'constant-vus',
      vus,
      duration: `${durationSeconds}s`,
      gracefulStop: `${gracefulStopSeconds}s`,
    },
  };
  return options;
}
