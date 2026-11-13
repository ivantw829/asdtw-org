const INVITE_CODE = 'b8BwFtv3C9';

async function getServerMembers() {
  const res = await fetch(`https://discord.com/api/v10/invites/${INVITE_CODE}?with_counts=true&with_expiration=true&with_permissions=true`);
  const data = await res.json();
  return data.approximate_member_count;
}
