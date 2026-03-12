import type { GetServerSideProps } from 'next';
import { TOOLS } from '@/data/tools';
import { getToolPathById } from '@/lib/seo/routes';

export default function LegacyToolRoute() {
  return null;
}

export const getServerSideProps: GetServerSideProps = async ({ params }) => {
  const id = params?.id as string;
  const tool = TOOLS.find((candidate) => candidate.id === id);

  if (!tool) {
    return { notFound: true };
  }

  return {
    redirect: {
      destination: getToolPathById(tool.id),
      permanent: true,
    },
  };
};
