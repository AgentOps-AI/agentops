import { NavbarClient } from './navbar-client';

export function Navbar({ mobile }: { mobile: boolean }) {
  return <NavbarClient mobile={mobile} />;
}
