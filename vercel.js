// src/api.js
const API_URL = import.meta.env.VITE_API_URL;

export async function getPosts() {
  const res = await fetch(`webapp-blond-beta.vercel.app/api/posts/`);
  const data = await res.json();
  return data;
}
