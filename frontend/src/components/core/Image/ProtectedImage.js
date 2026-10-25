import React, { useEffect, useState } from "react";
import Image from "@core/Image/Image";
import { useApi } from "@hooks/useApi";
import { storageUrlToApiPath } from "@utils/storagePath";

// Obrázek chráněný autorizací (profilová fotka): načte se přes API s tokenem jako blob.
// data:/blob: URL (náhled právě vybraného souboru) se zobrazí přímo.
export default function ProtectedImage({ src, ...rest }) {
    const api = useApi();
    const [objectUrl, setObjectUrl] = useState(null);
    const apiPath = storageUrlToApiPath(src);

    useEffect(() => {
        if (!apiPath) return undefined;
        let revoked = false;
        let created = null;
        api.get(apiPath, { responseType: "blob" })
            .then((res) => {
                if (revoked) return;
                created = URL.createObjectURL(res.data);
                setObjectUrl(created);
            })
            .catch(() => setObjectUrl(null));
        return () => {
            revoked = true;
            if (created) URL.revokeObjectURL(created);
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [apiPath]);

    if (apiPath) return objectUrl ? <Image src={objectUrl} {...rest} /> : null;
    return <Image src={src} {...rest} />;
}
