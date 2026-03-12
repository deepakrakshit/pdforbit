import type { GetServerSideProps } from 'next';

export const getServerSideProps: GetServerSideProps = async () => ({
  redirect: {
    destination: '/api-docs',
    permanent: false,
  },
});

export default function DocsRedirectPage() {
  return null;
}