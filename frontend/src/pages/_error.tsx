import type { NextPageContext } from 'next';

import ErrorScreen from '@/components/ErrorScreen';

type CustomErrorPageProps = {
  statusCode: number;
};

function resolveStatusCode(context: NextPageContext): number {
  if (context.res?.statusCode) {
    return context.res.statusCode;
  }
  if (typeof context.err?.statusCode === 'number') {
    return context.err.statusCode;
  }
  return 500;
}

export default function CustomErrorPage({ statusCode }: CustomErrorPageProps) {
  return <ErrorScreen statusCode={statusCode} />;
}

CustomErrorPage.getInitialProps = (context: NextPageContext) => {
  return {
    statusCode: resolveStatusCode(context),
  };
};