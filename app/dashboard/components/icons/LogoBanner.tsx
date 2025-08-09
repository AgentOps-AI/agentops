import Image from 'next/image';

const LogoBanner = () => (
  <Image
    src="/logo-banner.svg"
    alt="AgentOps Logo"
    width={140}
    height={30}
    priority
    style={{ height: 'auto' }}
    className="dark:invert"
  />
);

export default LogoBanner;
