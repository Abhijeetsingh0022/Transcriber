import StudioWorkspace from "./StudioWorkspace";

export function generateStaticParams() {
  return [{ jobId: "export" }];
}

export default function Page() {
  return <StudioWorkspace />;
}
