import React, { useEffect, useState } from 'react';

export function GithubStars() {
  const [stars, setStars] = useState(null);

  useEffect(() => {
    async function fetchStars() {
      const response = await fetch('https://api.github.com/repos/AgentOps-AI/agentops');
      const data = await response.json();
      const stars = Math.ceil(data.stargazers_count / 1000) * 1000;
      setStars(stars.toLocaleString());
    }
    fetchStars();
  }, []);

  return <p>{stars ? `${stars}th` : '2,000th'}</p>;
}