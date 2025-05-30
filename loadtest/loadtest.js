import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '30s', target: 10 },  // tăng tải đến 10 người dùng
    { duration: '1m', target: 10 },   // giữ tải 10 người dùng trong 1 phút
    { duration: '20s', target: 0 },   // giảm tải xuống 0
  ],
};

export default function () {
  const url = 'https://api.willdzai04.asia/predict'; // Thay bằng IP hoặc domain thật
  const payload = JSON.stringify({
    country: "United Kingdom",
    freq: "D",
    periods: 30
  });

  const params = {
    headers: { 'Content-Type': 'application/json' },
  };

  let res = http.post(url, payload, params);

  check(res, {
    'status 200': (r) => r.status === 200,
    'has data': (r) => r.json().length > 0,
  });

  sleep(1); // nghỉ 1 giây giữa các request
}
