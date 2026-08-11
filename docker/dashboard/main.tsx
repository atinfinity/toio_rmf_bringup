// toio フリート向け rmf-web ダッシュボードの設定。
//
// rmf-web の examples/demo/main.tsx を差し替える形でビルドする
// (docker/dashboard/Dockerfile 参照)。upstream のデモ設定は数十m級の
// 建物と rmf_demos のフリートを前提にしているため、そのままでは
// toio マット(A3 で 0.42 x 0.30 m)には使えない。

import '@fontsource/roboto/300.css';
import '@fontsource/roboto/400.css';
import '@fontsource/roboto/500.css';
import '@fontsource/roboto/700.css';

import ReactDOM from 'react-dom/client';
import {
  InitialWindow,
  LocallyPersistentWorkspace,
  MicroAppManifest,
  RmfDashboard,
  Workspace,
} from 'rmf-dashboard-framework/components';
import {
  createMapApp,
  robotMutexGroupsApp,
  robotsApp,
  tasksApp,
} from 'rmf-dashboard-framework/micro-apps';
import { StubAuthenticator } from 'rmf-dashboard-framework/services';

// ---------------------------------------------------------------------------
// ビルド時に差し替えられる設定
//
// Vite は VITE_ 接頭辞の環境変数をビルド時に埋め込む。compose.yaml の
// build.args から渡す想定で、未指定ならここの既定値を使う。
// 環境変数が反映されない場合はこのファイルの既定値を直接書き換えて
// 再ビルドすればよい。
// ---------------------------------------------------------------------------
const env = import.meta.env as unknown as Record<string, string | undefined>;

const str = (key: string, fallback: string): string => {
  const value = env[key];
  return value === undefined || value === '' ? fallback : value;
};

const num = (key: string, fallback: number): number => {
  const raw = env[key];
  if (raw === undefined || raw === '') {
    return fallback;
  }
  const value = Number(raw);
  return Number.isFinite(value) ? value : fallback;
};

// ズームは「1メートルあたりのピクセル数」(線形)。camera.zoom が
// react-three-fiber のピクセル基準フラスタムに渡るため、2^z ではない。
// デモの既定 6 は 6 px/m で数十m級の建物向け。A4 マット(0.297 x 0.210 m)を
// 画面いっぱいに出すには 2000 前後が要る(実測: 2000 で 569 x 369 px)。
const DEFAULT_ZOOM = num('VITE_TOIO_DEFAULT_ZOOM', 2000);
const DEFAULT_ROBOT_ZOOM = num('VITE_TOIO_DEFAULT_ROBOT_ZOOM', 4000);

const API_SERVER_URL = str('VITE_TOIO_API_SERVER_URL', 'http://localhost:8000');
// トラジェクトリサーバは rmf_visualization の schedule_visualizer_node が
// 既定ポート 8006 で立てる。toio_rmf.launch.py がすでに起動している
const TRAJECTORY_SERVER_URL = str('VITE_TOIO_TRAJECTORY_SERVER_URL', 'http://localhost:8006');

const mapApp = createMapApp({
  attributionPrefix: 'Open-RMF / toio',
  // toio_rmf_maps の building.yaml で定義しているレベル名
  defaultMapLevel: 'L1',
  defaultRobotZoom: DEFAULT_ROBOT_ZOOM,
  defaultZoom: DEFAULT_ZOOM,
});

// toio_rmf.launch.py は door / lift supervisor を起動しない(マット上に
// ドアもエレベータも無いため)ので、対応するアプリは載せていない。
const appRegistry: MicroAppManifest[] = [mapApp, robotsApp, robotMutexGroupsApp, tasksApp];

const homeWorkspace: InitialWindow[] = [{ layout: { x: 0, y: 0, w: 12, h: 6 }, microApp: mapApp }];

const robotsWorkspace: InitialWindow[] = [
  { layout: { x: 0, y: 0, w: 7, h: 4 }, microApp: robotsApp },
  { layout: { x: 8, y: 0, w: 5, h: 8 }, microApp: mapApp },
  { layout: { x: 0, y: 4, w: 7, h: 4 }, microApp: robotMutexGroupsApp },
];

const tasksWorkspace: InitialWindow[] = [
  { layout: { x: 0, y: 0, w: 7, h: 8 }, microApp: tasksApp },
  { layout: { x: 8, y: 0, w: 5, h: 8 }, microApp: mapApp },
];

export default function App() {
  return (
    <RmfDashboard
      apiServerUrl={API_SERVER_URL}
      trajectoryServerUrl={TRAJECTORY_SERVER_URL}
      authenticator={new StubAuthenticator()}
      helpLink="https://osrf.github.io/ros2multirobotbook/rmf-core.html"
      reportIssueLink="https://github.com/atinfinity/toio_rmf_bringup/issues"
      resources={{ fleets: {}, logos: { header: '/resources/defaultLogo.png' } }}
      tasks={{
        // フリート側は loop(patrol)と delivery が有効だが、ダッシュボード
        // からの delivery 投入は未検証のため patrol のみ並べる(docs/TASKS.md)
        allowedTasks: [{ taskDefinitionId: 'patrol' }],
        pickupZones: [],
        cartIds: [],
      }}
      tabs={[
        {
          name: 'Map',
          route: '',
          element: <Workspace initialWindows={homeWorkspace} />,
        },
        {
          name: 'Robots',
          route: 'robots',
          element: <Workspace initialWindows={robotsWorkspace} />,
        },
        {
          name: 'Tasks',
          route: 'tasks',
          element: <Workspace initialWindows={tasksWorkspace} />,
        },
        {
          name: 'Custom',
          route: 'custom',
          element: (
            <LocallyPersistentWorkspace
              defaultWindows={[]}
              allowDesignMode
              appRegistry={appRegistry}
              storageKey="custom-workspace"
            />
          ),
        },
      ]}
    />
  );
}

const root = ReactDOM.createRoot(document.getElementById('root') as HTMLElement);
root.render(<App />);
