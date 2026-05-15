import http from 'k6/http'
import { check, sleep } from 'k6'
import exec from 'k6/execution'

const BASE_URL = (__ENV.BASE_URL || 'http://localhost:8000/api').replace(/\/$/, '')
const ADMIN_USERNAME = __ENV.ADMIN_USERNAME || 'ADMIN'
const ADMIN_PASSWORD = __ENV.ADMIN_PASSWORD || 'ADMIN'
const USER_COUNT = Number(__ENV.USER_COUNT || 1000)
const RATE = Number(__ENV.RATE || 1000)
const DURATION = __ENV.DURATION || '1s'
const SETUP_TIMEOUT = __ENV.SETUP_TIMEOUT || '10m'
const PRE_ALLOCATED_VUS = Number(__ENV.PRE_ALLOCATED_VUS || 1000)
const MAX_VUS = Number(__ENV.MAX_VUS || 2000)
const SETUP_BATCH_SIZE = Number(__ENV.SETUP_BATCH_SIZE || 100)
const REGISTRATION_WINDOW_SECONDS = Number(__ENV.REGISTRATION_WINDOW_SECONDS || 120)
const EVENT_DURATION_SECONDS = Number(__ENV.EVENT_DURATION_SECONDS || 900)
const QR_WINDOW_SECONDS = Number(__ENV.QR_WINDOW_SECONDS || 300)

export const options = {
  setupTimeout: SETUP_TIMEOUT,
  scenarios: {
    qr_scan_traffic: {
      executor: 'constant-arrival-rate',
      rate: RATE,
      timeUnit: '1s',
      duration: DURATION,
      preAllocatedVUs: PRE_ALLOCATED_VUS,
      maxVUs: MAX_VUS,
    },
  },
  thresholds: {
    'http_req_failed{endpoint:qr_scan}': ['rate<0.05'],
    'http_req_duration{endpoint:qr_scan}': ['p(95)<1000'],
    checks: ['rate>0.95'],
  },
}

function formEncode(data) {
  return Object.entries(data)
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
    .join('&')
}

function isoFromNow(seconds) {
  return new Date(Date.now() + seconds * 1000).toISOString()
}

function authHeader(token) {
  return { Authorization: `Bearer ${token}` }
}

function login(username, password) {
  const response = http.post(
    `${BASE_URL}/auth/login`,
    formEncode({ username, password }),
    { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } },
  )

  check(response, {
    [`login ${username} succeeded`]: (r) => r.status === 200 && !!r.json('access_token'),
  })

  return response.json('access_token')
}

function batchRequests(requests, batchSize = SETUP_BATCH_SIZE) {
  const responses = []

  for (let index = 0; index < requests.length; index += batchSize) {
    const chunk = requests.slice(index, index + batchSize)
    responses.push(...http.batch(chunk))
  }

  return responses
}

export function setup() {
  const adminToken = login(ADMIN_USERNAME, ADMIN_PASSWORD)
  const runId = `${Date.now()}`
  const registrationStart = isoFromNow(-60)
  const registrationEnd = isoFromNow(REGISTRATION_WINDOW_SECONDS)
  const eventStart = isoFromNow(REGISTRATION_WINDOW_SECONDS + 5)
  const eventEnd = isoFromNow(REGISTRATION_WINDOW_SECONDS + 5 + EVENT_DURATION_SECONDS)

  const eventResponse = http.post(
    `${BASE_URL}/events/`,
    formEncode({
      title: `QR Load Test ${runId}`,
      description: 'k6 QR attendance load test event',
      point: '1',
      registration_start: registrationStart,
      registration_end: registrationEnd,
      event_start: eventStart,
      event_end: eventEnd,
      form_fields: '[]',
      location: 'k6-load-test',
      max_participants: String(USER_COUNT + 100),
    }),
    {
      headers: {
        ...authHeader(adminToken),
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    },
  )

  check(eventResponse, {
    'event created': (r) => r.status === 200 || r.status === 201,
  })

  const eventId = eventResponse.json('id')
  if (!eventId) {
    throw new Error(`Cannot create event: ${eventResponse.status} ${eventResponse.body}`)
  }

  const users = Array.from({ length: USER_COUNT }, (_, index) => {
    const suffix = `${runId}_${index}`
    return {
      full_name: `K6 User ${index}`,
      email: `k6_${suffix}@example.com`,
      password: '123456',
      student_id: `K6_${suffix}`,
      class_name: 'K6_LOAD',
    }
  })

  const createUserRequests = users.map((user) => ({
    method: 'POST',
    url: `${BASE_URL}/users`,
    body: formEncode(user),
    params: {
      headers: {
        ...authHeader(adminToken),
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    },
  }))
  const createUserResponses = batchRequests(createUserRequests)
  check(null, {
    'users created': () => createUserResponses.every((r) => r.status === 201),
  })

  const loginRequests = users.map((user) => ({
    method: 'POST',
    url: `${BASE_URL}/auth/login`,
    body: formEncode({
      username: user.student_id,
      password: user.password,
    }),
    params: {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    },
  }))
  const loginResponses = batchRequests(loginRequests)
  const userTokens = loginResponses.map((response, index) => {
    const token = response.json('access_token')
    if (!token) {
      throw new Error(`Cannot login user index=${index}: ${response.status} ${response.body}`)
    }
    return token
  })

  const registerRequests = userTokens.map((token) => ({
    method: 'POST',
    url: `${BASE_URL}/events/${eventId}/register_public_event`,
    body: JSON.stringify({ answers: [] }),
    params: {
      headers: {
        ...authHeader(token),
        'Content-Type': 'application/json',
      },
    },
  }))
  const registerResponses = batchRequests(registerRequests)
  check(null, {
    'users registered event': () => registerResponses.every((r) => r.status === 201),
  })

  const waitUntilEventStartSeconds = Math.ceil(
    (new Date(eventStart).getTime() - Date.now()) / 1000,
  )
  if (waitUntilEventStartSeconds > 0) {
    console.log(`Waiting ${waitUntilEventStartSeconds}s until event_start before opening QR session`)
    sleep(waitUntilEventStartSeconds)
  }

  const sessionResponse = http.post(
    `${BASE_URL}/attendance/events/${eventId}/sessions`,
    JSON.stringify({
      window_seconds: QR_WINDOW_SECONDS,
    }),
    {
      headers: {
        ...authHeader(adminToken),
        'Content-Type': 'application/json',
      },
    },
  )

  check(sessionResponse, {
    'qr session opened': (r) => r.status === 201 && !!r.json('windows.0.qr_value'),
  })

  const sessionId = sessionResponse.json('session_id')
  const qrValue = sessionResponse.json('windows.0.qr_value')
  if (!qrValue) {
    throw new Error(`Cannot open QR session: ${sessionResponse.status} ${sessionResponse.body}`)
  }

  console.log(
    `Prepared QR load test. event_id=${eventId}, session_id=${sessionId}, users=${userTokens.length}, rate=${RATE}/s, duration=${DURATION}`,
  )

  return {
    eventId,
    sessionId,
    qrValue,
    userTokens,
  }
}

export default function (data) {
  const tokenIndex = exec.scenario.iterationInTest % data.userTokens.length
  const token = data.userTokens[tokenIndex]

  const response = http.post(
    `${BASE_URL}/attendance/scan`,
    JSON.stringify({
      qr_value: data.qrValue,
    }),
    {
      headers: {
        ...authHeader(token),
        'Content-Type': 'application/json',
      },
      tags: {
        endpoint: 'qr_scan',
      },
    },
  )

  check(response, {
    'scan queued': (r) => r.status === 202,
  })
}
