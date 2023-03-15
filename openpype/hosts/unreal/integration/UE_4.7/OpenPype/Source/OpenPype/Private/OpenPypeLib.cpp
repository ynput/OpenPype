#include "OpenPypeLib.h"
#include "Misc/Paths.h"
#include "Misc/ConfigCacheIni.h"
#include "UObject/UnrealType.h"

/**
 * Sets color on folder icon on given path
 * @param InPath - path to folder
 * @param InFolderColor - color of the folder
 * @warning This color will appear only after Editor restart. Is there a better way?
 */

void UOpenPypeLib::CSetFolderColor(FString FolderPath, FLinearColor FolderColor, bool bForceAdd)
{
	auto SaveColorInternal = [](FString InPath, FLinearColor InFolderColor)
	{
		// Saves the color of the folder to the config
		if (FPaths::FileExists(GEditorPerProjectIni))
		{
			GConfig->SetString(TEXT("PathColor"), *InPath, *InFolderColor.ToString(), GEditorPerProjectIni);
		}

	};

	SaveColorInternal(FolderPath, FolderColor);

}
/**
 * Returns all poperties on  given object
 * @param cls - class
 * @return TArray of properties
 */
TArray<FString> UOpenPypeLib::GetAllProperties(UClass* cls)
{
	TArray<FString> Ret;
	if (cls != nullptr)
	{
		for (TFieldIterator<FProperty> It(cls); It; ++It)
		{
			FProperty* Property = *It;
			if (Property->HasAnyPropertyFlags(EPropertyFlags::CPF_Edit))
			{
				Ret.Add(Property->GetName());
			}
		}
	}
	return Ret;
}
