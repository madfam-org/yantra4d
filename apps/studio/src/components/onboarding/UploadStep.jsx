import { Upload, ChevronRight } from "lucide-react"
import { Button } from "@/components/ui/button"

export default function UploadStep({ slug, setSlug, files, handleFileDrop, handleAnalyze, loading, t }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="text-lg font-semibold">{t("onboard.upload_title")}</div>

      <div>
        <label className="text-sm font-medium">{t("onboard.slug_label")}</label>
        <input
          type="text"
          value={slug}
          onChange={(e) => setSlug(e.target.value.replace(/[^a-z0-9-_]/gi, ""))}
          className="w-full mt-1 px-3 py-2 rounded-md border border-border bg-background text-sm"
          placeholder={t("onboard.slug_placeholder")}
        />
      </div>

      <div
        onDrop={handleFileDrop}
        onDragOver={(e) => e.preventDefault()}
        className="border-2 border-dashed border-border rounded-lg p-8 text-center cursor-pointer hover:border-primary/50 transition-colors"
      >
        <Upload className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">
          {t("onboard.drop_text")}
        </p>
        <input
          type="file"
          multiple
          accept=".scad"
          onChange={handleFileDrop}
          className="hidden"
          id="scad-upload"
        />
        <label htmlFor="scad-upload" className="text-primary text-sm underline cursor-pointer">
          {t("onboard.browse")}
        </label>
      </div>

      {files.length > 0 && (
        <div className="text-sm">
          <div className="font-medium mb-1">{files.length} {t("onboard.files_selected")}</div>
          <ul className="list-disc list-inside text-muted-foreground">
            {files.map((f) => (
              <li key={f.name}>{f.name}</li>
            ))}
          </ul>
        </div>
      )}

      <Button onClick={handleAnalyze} disabled={files.length === 0 || loading}>
        {loading ? t("onboard.analyzing") : t("onboard.analyze_btn")}
        <ChevronRight className="h-4 w-4 ml-1" />
      </Button>
    </div>
  )
}
