let r;
var d = (o) => {
    if (!r) {
        let e = function(n, t) {
            return o.createElement("svg", {width: "100%", height: "1.5em", strokeWidth: 1.5, viewBox: "0 0 24 24", fill: "none", xmlns: "http://www.w3.org/2000/svg", color: "currentColor", ref: t, ...n}, o.createElement("path", {d: "M6 20h12M12 4v12m0 0l3.5-3.5M12 16l-3.5-3.5", stroke: "currentColor", strokeLinecap: "round", strokeLinejoin: "round"}));
        };
        r = o.forwardRef(e);
    }
    return r;
};
const __FramerMetadata__ = {exports: {default: {type: "reactComponent", slots: [], annotations: {framerContractVersion: "1"}}, __FramerMetadata__: {type: "variable"}}};
export { __FramerMetadata__, d as default };