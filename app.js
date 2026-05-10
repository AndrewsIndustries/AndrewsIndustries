// Fetch both feeds and combine them
const worldData = await fetch(worldUrl).then(res => res.json());
const localData = await fetch(localUrl).then(res => res.json());

const allArticles = [...worldData.articles, ...localData.articles];
const tickerText = allArticles.map(a => a.title).join('  •  ');