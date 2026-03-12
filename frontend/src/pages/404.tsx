import ErrorScreen from '@/components/ErrorScreen';

export default function NotFoundPage() {
  return (
    <ErrorScreen
      statusCode={404}
      title="This page isn’t in our orbit."
      message="The destination you tried to reach doesn't exist or may have been relocated. Head back to PdfORBIT and continue managing your PDFs without interruption."
    />
  );
}